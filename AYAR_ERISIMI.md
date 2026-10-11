# Ayar yönetimi ve API anahtarları — F58

`/settings`, `GET/POST /api/settings` ve `POST /api/test-connection` zorunlu yönetici doğrulaması kullanır. Ayar yanıtından `api_key` çıkarılır; kısa anahtarlar da gizlenir. Kayıtlı anahtar tarayıcıdaki parola alanına doldurulmaz. Ayar dosyası geçici dosya üzerinden atomik olarak, yalnız dosya sahibine okuma/yazma izniyle kaydedilir.

## Coolify yapılandırması

1. Dağıtımdan önce OMC uygulamasının ortam değişkenlerine rastgele üretilmiş, en az 32 baytlık `OMC_API_TOKEN` ekleyin. Örnek dosyadaki değer boştur. Gerçek değeri Git'e veya sohbete yazmayın.
2. HTTPS üzerinden `/settings` açın. Tarayıcının giriş penceresinde kullanıcı adı `yonetici`, parola olarak `OMC_API_TOKEN` kullanılır. Tarayıcı aynı origin üzerindeki API isteklerinde bu kimlik bilgisini gönderir. Komut satırı istemcileri `Authorization: Bearer ...` kullanabilir. URL/sorgu parametresinden anahtar kabul edilmez.
3. Coolify TLS proxy arkasında `OMC_SETTINGS_ORIGIN` değerini uygulamanın dış adresine, örneğin `https://omc.example.com` biçiminde ayarlayın; yol, sorgu veya kullanıcı bilgisi eklemeyin. Ayar yazarken şema, alan adı ve port bu değerle karşılaştırılır. Değer boşsa isteğin `base_url` adresi kullanılır; proxy dış HTTPS şemasını iletmiyorsa yazma 403 ile reddedilir.
4. Yönetici anahtarı eksik/kısa veya verilen origin geçersiz ise web sunucusu başlamaz. Bütün kopyalara aynı doğru yapılandırmayı uygulayın; doğrulama her istekte çalışır. Başka bir origin'den ayar yazma isteği reddedilir. Hassas yanıtlar `Cache-Control: no-store` taşır.

Bu ayrı bir yönetici anahtarıdır; ekip üyeliği veya bir ekip kullanıcısının token'ı ayar erişimi sağlamaz. Genel ekip, paylaşım, görev ve geçmiş rotaları için yeni bir rol/oturum sistemi eklenmemiştir. Geçmiş API'sinin mevcut import sırasında alınan token davranışı bu değişiklikle yenilenmez.

## Sağlayıcı anahtarını değiştirme

API Anahtarları bölümünde yeni anahtarı girip **Kaydet** seçin. Yeni değer sunucuya kaydedilir ve alan tekrar boşalır. Alanı boş bırakarak diğer ayarları kaydetmek mevcut anahtarı korur. Maskeli değer de mevcut anahtarı değiştirmez. **Sıfırla** mevcut anahtarı açıkça siler. Dosyadaki eski anahtar otomatik olarak döndürülmez.

**Test** boş alanla da çalışır: sunucu kayıtlı anahtarı ve kayıtlı sağlayıcı adresini kullanır. Yeni adresi önce kaydedin. Özel sağlayıcı için model kimliği de kaydedilir. Girilmiş yeni anahtarla test, girilmiş adrese yapılır. Gerçek bağlantı testi sağlayıcının API'sine istek gönderir ve ücret oluşturabilir. Otomatik testlerde yalnız kurgusal veriler ve sağlayıcı yanıt taklitleri kullanılır.

`OMC_API_TOKEN` değiştiğinde çalışan süreçteki eski Basic/Bearer kimlik bilgisi ayar erişiminde reddedilir. Coolify ortam değişikliği süreçlerin yeniden başlatılmasını gerektirir. Tarayıcı eski Basic parolasını tutuyorsa özel pencereyi kapatıp yeni pencerede tekrar giriş yapın. Tarayıcı depolamasına yönetici anahtarı eklenmez. Özel model/sağlayıcıların daha önce mevcut olan kullanıcı tarafından girilen yerel tarayıcı kayıtları bu çalışmanın kapsamında taşınmaz; hassas anahtarları ortak tarayıcılarda saklamayın.

## Doğrulama

`python scripts/test-settings-security.py` gerçek FastAPI HTTP doğrulaması ve geçici ayar dosyasıyla güvenlik ve mevcut web regresyonlarını çalıştırır. Import sırasında SQLite oluşturan modüller yalnız test sürecinde geçici kullanıcı dizinine yönlendirilir; `HOME` değiştirilmez. Test sürecinde gerçek TCP bağlantıları kapalıdır; sağlayıcı/HTTP yanıtları testlerin kendi taklitleriyle verilir. `node --test tests/settings-client-security.test.mjs` sayfanın JavaScript sözdizimini ve gerçek sayfa işlevlerini DOM/HTTP taklitleriyle kontrol eder. Bunlar gerçek tarayıcı veya canlı Coolify kabul testi değildir.

Uygulama dağıtımı, gerçek token/sağlayıcı anahtarı değişikliği ve mevcut dosya izinlerinin üretimde doğrulanması ayrıca yapılmalıdır. [FastAPI HTTP Basic belgeleri](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/) tarayıcı giriş istemini ve zaman karşılaştırması yaklaşımını açıklar.
