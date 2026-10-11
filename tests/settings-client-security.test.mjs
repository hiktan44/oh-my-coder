import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../src/web/templates/settings.html', import.meta.url), 'utf8');
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
