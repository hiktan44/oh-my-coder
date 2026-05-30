# Oh My Coder Resmi Sitesi

## Dağıtım Yöntemi

### GitHub Pages (Önerilen)

1. Depo ayarlarına gidin: `Settings > Pages`
2. Source için **Deploy from a branch** seçin
3. Branch: `main`, Folder: `/website`
4. Kaydedin ve 1-2 dakika bekleyin
5. Erişim: `https://vobc.github.io/oh-my-coder`

### Yerel Önizleme

```bash
# website dizinine gir
cd website

# Python basit sunucu
python3 -m http.server 8080

# Veya Node.js
npx serve .
```

## Dosya Yapısı

```
website/
├── index.html      # Ana sayfa (tek sayfa uygulama)
├── README.md       # Bu dosya
└── CNAME           # Özel alan adı (isteğe bağlı)
```

## Özel Alan Adı (İsteğe Bağlı)

1. `CNAME` dosyasına alan adını yazın, örneğin: `oh-my-coder.com`
2. Alan adı sağlayıcınızda `vobc.github.io` adresine bir CNAME kaydı ekleyin
3. GitHub Pages ayarlarında özel alan adını yapılandırın

## Teknoloji Yığını

- Saf HTML + CSS + JavaScript
- Derleme aracı yok, bağımlılık yok
- Duyarlı tasarım, mobil cihaz desteği
