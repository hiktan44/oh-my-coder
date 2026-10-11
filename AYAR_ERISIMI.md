# Yönetici erişimi ve API anahtarları — F58

Ana FastAPI uygulamasındaki özel sayfalar, görev/sohbet başlatma, görev/geçmiş okuma ve silme, SSE, ekip, model, oturum ve ayar işlemleri zorunlu yönetici doğrulaması kullanır. Giriş olmadan bu rotalar 401 döndürür. Ayar yanıtından `api_key` çıkarılır; kısa anahtarlar da gizlenir. Kayıtlı anahtar tarayıcıdaki parola alanına doldurulmaz. Ayar dosyası geçici dosya üzerinden atomik olarak, yalnız dosya sahibine okuma/yazma izniyle kaydedilir.

`GET/HEAD /health`, statik/PWA dosyaları ve `GET/HEAD /api/share/{8 haneli hex kimlik}` herkese açık kalır. Paylaşım kimliğiyle okuma mevcut yayımlama davranışıdır; kimliği bilen kişi paylaşımı okuyabilir ve mevcut son kullanma tarihi kontrol edilir. Paylaşım listesi, oluşturma, içe aktarma ve silme yönetici gerektirir. Yeni bir paylaşım parolası veya daha güçlü paylaşım kimliği eklenmemiştir.

## Coolify yapılandırması

1. Dağıtımdan önce OMC uygulamasının ortam değişkenlerine rastgele üretilmiş, en az 32 baytlık `OMC_API_TOKEN` ekleyin. Örnek dosyadaki değer boştur. Gerçek değeri Git'e veya sohbete yazmayın.
2. HTTPS üzerinden ana sayfayı veya `/settings` açın. Tarayıcının giriş penceresinde kullanıcı adı `yonetici`, parola olarak `OMC_API_TOKEN` kullanılır. Tarayıcı aynı origin üzerindeki API/SSE isteklerinde bu kimlik bilgisini gönderir. Komut satırı istemcileri `Authorization: Bearer ...` kullanabilir. URL/sorgu parametresinden anahtar kabul edilmez.
3. Coolify TLS proxy arkasında `OMC_SETTINGS_ORIGIN` değerini uygulamanın dış adresine, örneğin `https://omc.example.com` biçiminde ayarlayın; yol, sorgu veya kullanıcı bilgisi eklemeyin. Bütün özel yazma işlemlerinde şema, alan adı ve port bu değerle karşılaştırılır. Değer boşsa isteğin `base_url` adresi kullanılır; proxy dış HTTPS şemasını iletmiyorsa yazma 403 ile reddedilir.
4. Yönetici anahtarı eksik/kısa veya verilen origin geçersiz ise web sunucusu başlamaz. Bütün kopyalara aynı doğru yapılandırmayı uygulayın; doğrulama her özel istekte çalışır. Başka bir origin'den yazma isteği reddedilir. Özel yanıtlar ve yayımlanmış paylaşım yanıtları `Cache-Control: no-store` taşır.

Bu tek sahibi olan web sunucusunun yönetici anahtarıdır; ekip üyeliği veya ekip kullanıcısının token'ı erişim sağlamaz. Müşteri/ekip bazında çok kullanıcılı yetkilendirme eklenmemiştir. Ana uygulamada geçmiş ve görev silme aynı güncel Basic/Bearer doğrulamasını kullanır; modülün import anındaki eski token'ı bu girişle çakışmaz. Tek başına başka bir FastAPI uygulamasına eklenen eski geçmiş router'ının ayrı kullanım sözleşmesi değiştirilmemiştir; bu rehber `src.web.app:app` içindir.

Yeni service worker yalnız herkese açık statik dosyaları saklar; özel sayfalar, API ve SSE yanıtları çevrimdışı önbellekten sunulmaz. Yeni worker etkinleştiğinde uygulamanın eski `oh-my-coder-*` önbellekleri temizlenir. Dağıtımdan sonra tarayıcıyı yenileyip yeni worker'ın etkinleştiğini doğrulayın; daha önce alınmış bir kopyanın başka yerde tutulması geri alınamaz.

## Sağlayıcı anahtarını değiştirme

API Anahtarları bölümünde yeni anahtarı girip **Kaydet** seçin. Yeni değer sunucuya kaydedilir ve alan tekrar boşalır. Alanı boş bırakarak diğer ayarları kaydetmek mevcut anahtarı korur. Maskeli değer de mevcut anahtarı değiştirmez. **Sıfırla** mevcut anahtarı açıkça siler. Dosyadaki eski anahtar otomatik olarak döndürülmez.

**Test** boş alanla da çalışır: sunucu kayıtlı anahtarı ve kayıtlı sağlayıcı adresini kullanır. Yeni adresi önce kaydedin. Özel sağlayıcı için model kimliği de kaydedilir. Girilmiş yeni anahtarla test, girilmiş adrese yapılır. Gerçek bağlantı testi sağlayıcının API'sine istek gönderir ve ücret oluşturabilir. Otomatik testlerde yalnız kurgusal veriler ve sağlayıcı yanıt taklitleri kullanılır.

`OMC_API_TOKEN` değiştiğinde çalışan süreçteki eski Basic/Bearer kimlik bilgisi bütün özel rotalarda reddedilir. Coolify ortam değişikliği süreçlerin yeniden başlatılmasını gerektirir. Tarayıcı eski Basic parolasını tutuyorsa özel pencereyi kapatıp yeni pencerede tekrar giriş yapın. Tarayıcı depolamasına yönetici anahtarı eklenmez. Özel model/sağlayıcıların daha önce mevcut olan kullanıcı tarafından girilen yerel tarayıcı kayıtları bu çalışmanın kapsamında taşınmaz; hassas anahtarları ortak tarayıcılarda saklamayın.

## Doğrulama

`python scripts/test-settings-security.py` gerçek FastAPI HTTP doğrulaması ve geçici ayar dosyasıyla güvenlik ve mevcut web regresyonlarını çalıştırır. Import sırasında SQLite oluşturan modüller yalnız test sürecinde geçici kullanıcı dizinine yönlendirilir; `HOME` değiştirilmez. Test sürecinde gerçek TCP bağlantıları kapalıdır; sağlayıcı/HTTP yanıtları testlerin kendi taklitleriyle verilir. `node --test tests/settings-client-security.test.mjs` sayfanın JavaScript sözdizimini ve gerçek sayfa işlevlerini DOM/HTTP taklitleriyle kontrol eder. Bunlar gerçek tarayıcı veya canlı Coolify kabul testi değildir.

Uygulama dağıtımı, gerçek token/sağlayıcı anahtarı değişikliği ve mevcut dosya izinlerinin üretimde doğrulanması ayrıca yapılmalıdır. [FastAPI HTTP Basic belgeleri](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/) tarayıcı giriş istemini ve zaman karşılaştırması yaklaşımını açıklar.
