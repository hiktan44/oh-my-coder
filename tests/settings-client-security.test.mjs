import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../src/web/templates/settings.html', import.meta.url), 'utf8');
const workerSource = readFileSync(new URL('../src/web/static/pwa/sw.js', import.meta.url), 'utf8');
const inline = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match => match[1]).join('\n');
// Sayfanın tüm satır içi JavaScript'i de sözdizimi kontrolünden geçer.
new vm.Script(inline);
function section(start, end) {
  const offset = inline.indexOf(start);
  assert.ok(offset >= 0);
  const stop = inline.indexOf(end, offset);
  assert.ok(stop > offset);
  return inline.slice(offset, stop);
}

test('kayıtlı anahtar alanı boş kalır; yalnız maske görünür', async () => {
  const nodes = new Map();
  for (const id of ['key-deepseek', 'dot-deepseek', 'status-deepseek']) nodes.set(id, {value:'old-prefill'});
  const context = vm.createContext({
    document: {getElementById: id => nodes.get(id)},
    fetch: async () => ({json: async () => ({models:{deepseek:{has_key:true,api_key_masked:'****ABCD',api_key:'fictional-never-prefill'}}})}),
  });
  vm.runInContext(section('async function loadSettings()', '        loadSettings();'), context);
  await context.loadSettings();
  assert.equal(nodes.get('key-deepseek').value, '');
  assert.equal(nodes.get('key-deepseek').placeholder, '****ABCD');
  assert.equal(nodes.get('status-deepseek').textContent, 'Yapılandırıldı (****ABCD)');
});

test('boş alanla sağlayıcı testi kayıtlı sunucu anahtarını seçer', async () => {
  const calls=[];
  const button={classList:{remove(){},add(){},contains(){return false;}},parentElement:{querySelector(){return null;}}};
  const context=vm.createContext({
    document:{getElementById:id => id.startsWith('btn-') ? button : {value:''}},
    showToastSmall(){}, setTimeout(){},
    fetch:async (url, options) => {calls.push({url,body:JSON.parse(options.body)});return {json:async()=>({ok:true,msg:'tamam'})};},
  });
  vm.runInContext(section('async function testProvider(id)', '        // Save all providers at once'),context);
  await context.testProvider('deepseek');
  assert.equal(calls.length,1);
  assert.equal(calls[0].url,'/api/test-connection');
  assert.equal(calls[0].body.provider,'deepseek');
  assert.equal(calls[0].body.api_key,'');
});

test('özel sağlayıcı testi kayıtlı model adını gönderir', async () => {
  const calls=[];
  const button={classList:{remove(){},add(){}}};
  const context=vm.createContext({
    document:{getElementById:id => id.startsWith('btn-') ? button : {value:id.startsWith('url-')?'https://fixture.invalid':''}},
    getCustomProviders:()=>[{id:'fixture',model:'example-model'}],
    showToastSmall(){},
    fetch:async (url,options)=>{calls.push(JSON.parse(options.body));return {json:async()=>({ok:true,msg:'tamam'})};},
  });
  vm.runInContext(section('async function testCustomProvider(id)', '        function renderCustomProviders()'),context);
  await context.testCustomProvider('fixture');
  assert.equal(calls.length,1);
  assert.equal(calls[0].model_name,'custom_fixture');
  assert.equal(calls[0].api_key,'');
});

function workerFixture({status = 200, control = '', keys = ['oh-my-coder-v1', 'unrelated-app']} = {}) {
  const listeners = new Map();
  const state = {deleted: [], precached: [], writes: [], network: [], waits: []};
  const cache = {
    addAll: async paths => {state.precached.push(...paths);},
    put: async request => {state.writes.push(request.url);},
  };
  const context = vm.createContext({
    URL,
    self: {location: {origin: 'https://omc.fixture.invalid'},
      addEventListener: (name, callback) => listeners.set(name, callback),
      skipWaiting() {}, clients: {claim: async () => {}},
    },
    caches: {open: async () => cache, match: async () => undefined,
      keys: async () => keys, delete: async key => {state.deleted.push(key);return true;},
    },
    fetch: async request => {
      state.network.push(request.url);
      return {ok: status >= 200 && status < 300, status,
        headers: {get: () => control}, clone: () => ({})};
    },
  });
  vm.runInContext(workerSource, context);
  function invoke(name, request) {
    const event = {request, waitUntil: value => state.waits.push(value),
      respondWith: value => {event.response = value;}};
    listeners.get(name)(event);
    return event;
  }
  async function settle(event) {
    if (event.response) await event.response;
    await Promise.all(state.waits);
  }
  return {state, invoke, settle};
}

test('service worker özel sayfaları ve API/SSE yanıtlarını önbellekten sunmaz', async () => {
  const fixture = workerFixture();
  for (const [path, mode, destination] of [['/', 'navigate', 'document'],
    ['/settings', 'navigate', 'document'], ['/api/tasks', 'cors', ''],
    ['/sse/execute/fixture', 'cors', ''], ['/api/share/abcd1234', 'cors', '']]) {
    const event = fixture.invoke('fetch', {url: 'https://omc.fixture.invalid' + path,
      method: 'GET', mode, destination});
    assert.equal(event.response, undefined);
    await fixture.settle(event);
  }
  assert.deepEqual(fixture.state.writes, []);
  assert.deepEqual(fixture.state.network, []);
});

test('yeni service worker özel ana sayfayı önceden saklamaz ve eski uygulama önbelleğini temizler', async () => {
  const fixture = workerFixture();
  await fixture.settle(fixture.invoke('install'));
  assert.equal(fixture.state.precached.includes('/'), false);
  assert.ok(fixture.state.precached.includes('/manifest.webmanifest'));
  await fixture.settle(fixture.invoke('activate'));
  assert.deepEqual(fixture.state.deleted, ['oh-my-coder-v1']);
});

test('service worker hata veya no-store/private yanıtını saklamaz', async () => {
  for (const options of [{status: 401}, {status: 503}, {control: 'no-store'}, {control: 'private'}]) {
    const fixture = workerFixture(options);
    await fixture.settle(fixture.invoke('fetch', {url: 'https://omc.fixture.invalid/static/app.js', method: 'GET'}));
    assert.deepEqual(fixture.state.writes, []);
    assert.equal(fixture.state.network.length, 1);
  }
});

test('herkese açık başarılı statik dosya çevrimdışı önbelleğe alınabilir', async () => {
  const fixture = workerFixture();
  await fixture.settle(fixture.invoke('fetch', {url: 'https://omc.fixture.invalid/static/app.js', method: 'GET'}));
  assert.deepEqual(fixture.state.writes, ['https://omc.fixture.invalid/static/app.js']);
});
