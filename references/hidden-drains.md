# Hidden token drains C1–C50

Source: MinToken spec v3 Section C (verbatim, Turkish). Labels: [D] docs-verified · [G] observed in tool definitions · [R] third-party, UNVERIFIED · [I] inference, UNVERIFIED. Text after "→" is the MinToken action. Any action that changes settings needs diff + explicit approval.

## GRUP 1 — HER ISTEKTE TEKRAR ÖDENENLER

C1 [D] Her tool çağrısı ayrı bir API isteğidir ve o turun tüm tool sonuçlarını taşır; tek bir mesajın arkasında onlarca istek olabilir. → B5 freni, dar kapsamlı görev.
C2 [D] Cache'li yeniden okuma bile plan limitine yazılır; gün boyu açık oturumda tek satırlık soru bile tüm geçmişi okutur. → B4.
C3 [R] Taze oturumun başlangıç bağlamı ~41k token olarak raporlanmış (v2.1.123, GitHub issue; kullanıcı raporu). → /context ile kendi başlangıç yükünü ölçtür.
C4 [D] Ertelenmiş MCP'de bile araç adları ve server instructions bağlamda durur. → /mcp ile kullanılmayanı kapat.
C5 [D] alwaysLoad işaretli veya eşik tabanlı yüklenen MCP şemaları prefix'te kalır. → audit_tools.py listele.
C6 [D] Tool search olmayan ortamlarda (özel gateway, eski Vertex modelleri, Azure-Foundry) tüm MCP şemaları prefix'te. → B7 uyarısı.
C7 [G] Skill açıklamaları listesi her turda bağlamda duruyor. → skill sayısını az tut, description'ları dar yaz (MinToken'ınki dahil).
C8 [D] CLAUDE.md, auto memory ve kapsamsız rules her oturum başında yüklenir; /clear ve /compact sonrası yeniden. → CLAUDE.md <200 satır; iş akışı talimatlarını skill'e taşı (skill'ler çağrılınca yüklenir).
C9 [D] İç içe CLAUDE.md ve paths: kurallı rules, eşleşen dosya okununca sessizce bağlama eklenir. → alt dizin CLAUDE.md'lerini kısa tut.
C10 [D] Sistem promptuna çalışma dizini, platform, shell, OS, git status (dal, son commit'ler) gömülür. → sabit yük; kirli/uzun git status'ü temiz tut.
C11 [D] Dosya değişince araya <system-reminder> bildirimi eklenir; Claude gerekirse dosyayı yeniden okur. → oturum sırasında dışarıdan toplu dosya değişikliği (formatter, generator) yapma.
C12 [G] Her mesajda saat dilimi, bellek özeti, araç/ajan listeleri gibi sistem hatırlatmaları gelir ve biriken bağlama dahildir. → uzun oturumu temizle.
C13 [I] Hook çıktıları (ör. SessionStart/UserPromptSubmit) bağlama eklenebilir. → kendi hook'larımızın çıktısını kısa tut; hooks dokümanından doğrula.

## GRUP 2 — CACHE KAÇIRMALARI ("YENIDEN YAZMA" FATURALARI)

C14 [D] TTL aşılınca ara sonrası ilk mesaj tüm bağlamı yeniden işler; abonelikte 1 saat, API key/bulut/usage credits'te 5 dk. → B15.
C15 [D] Plan limiti dolup usage credits'e geçince ana konuşma TTL'i 1 saatten 5 dakikaya düşer. → promptCacheTtl=1h seçeneğini öner (maliyetini belirt).
C16 [D] Subagent, workflow, teammate, fork, compaction ve oturum başlığı istekleri varsayılan 5 dk kovasında. → subagentPromptCacheTtl'i sadece uzun subagent işlerinde düşün.
C17 [D] Her modelin kendi cache'i var; /model değişimi tüm geçmişi cache'siz okutur (cache sıcakken onay sorar, v2.1.238+). → modeli oturum başında seç.
C18 [D] opusplan: plan mode'a girip çıkmak her seferinde model değişimi = cache sıfırı. → opusplan'ı büyük bağlamda kullanma.
C19 [D] Güvenlik sınıflandırıcısı bir isteği işaretleyince otomatik model fallback = model değişimi. → fark etmeden olabilir; /usage'daki miss'lere bak.
C20 [D] /effort değişimi cache'i sıfırlar (cache anahtarı effort'u da içerir). → effort'u başta seç.
C21 [D] Fast mode'u açmak cache anahtarını değiştirir; ilk istek tüm geçmişi cache'siz, fast mode oranıyla okur. → derin oturumda açma.
C22 [D] Çıplak araç adını deny etmek (Bash, WebFetch) sistem promptunu değiştirir; kapsamlı deny güvenli. → B2.
C23 [D] Prefix'e yüklenen MCP sunucusu kopup otomatik yeniden bağlanırsa kullanıcı bir şey yapmadan cache bozulur. → kararsız server'ı kapat.
C24 [D] MCP sağlayan plugin'i oturum ortasında açıp kapamak (araçlar prefix'teyse) cache'i bozar. → /reload-plugins uyarısına dikkat; oturum başında yap.
C25 [D] Claude Code güncellemesi sonrası ilk istek baştan işlenir; güncelleme sonrası resume tüm geçmişi cache'siz okutur. → önemli uzun işte DISABLE_AUTOUPDATER=1 ile zamanı sen seç.
C26 [D] Gateway cache_control işaretlerini sessizce silerse tüm geçmiş HER turda cache'siz faturalanır. → gateway kullanıcısına /usage'daki cache read oranını kontrol ettir.
C27 [D] Cache dizin ve makineye özgü; farklı dizin/worktree'ler birbirinin cache'ini kullanamaz; aynı dizinde paralel oturumlar paylaşır. → worktree çoğaltmadan önce düşün.
C28 [D] /compact cache sıcakken ucuz, soğukken (eski oturumu resume) tüm geçmişi cache'siz özetler. → eski büyük oturumu resume etmeden önce "özetten devam" seçeneğini kullan.

## GRUP 3 — SEN MESAJ YAZMADAN ÇALIŞANLAR

C29 [D] Arka planda --resume için konuşma özetleme işleri çalışır (belgelenen: oturum başına tipik <$0.04). → küçük; bilgi ver.
C30 [D] Prompt suggestions açıkken her cevaptan sonra kısa bir istek gider (çoğu cache read). → kapatma yolunu doküman interactive-mode sayfasından doğrulayıp öner.
C31 [D] Oturum başlığı üretimi ve benzeri yardımcı istekler ayrı kovada çalışır. → tek tek önemsiz; toplamı /usage'da gör.
C32 [D] /usage gibi bazı komutlar durum isteği üretir. → gereksiz sık çalıştırma.
C33 [D] Zamanlanmış görev ve /loop, oturum boştayken bile her tetiklemede TÜM bağlamı gönderir. → /usage'daki "Loops" satırına bak; gereksiz loop'u durdur.
C34 [D] Başka oturumdan gelen mesaj, boştaki oturumu yeni bir tur olarak uyandırır ve tüm bağlamı gönderir. → crossSessionInbound=hold ayarını öner.
C35 [D] Arka plan işi bekleyen aktif goal, oturum boşken bile check-in turu başlatır (goal başına en çok 3, v2.1.246+). → CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0.
C36 [D] /insights en çok 200 oturumu analiz eder ve tokenları planından yer. → ayda birkaç kez, sık değil.
C37 [R] Auto mode, yan etkili tool çağrısından önce ayrı bir sınıflandırıcı model çağrısı yapıyor olabilir (üçüncü taraf araştırma deposu; doğrulanmadı). → kullanıcıya "doğrulanmadı" diyerek /usage attribution'a bakmasını söyle.
C38 [D] Pencere dolunca otomatik compaction ayrı büyük bir istektir ve zamanı senin kontrolünde değildir. → doğal molada elle /compact; auto-compact penceresi model-config sayfasındaki ayardan değiştirilebilir (adı dokümandan doğrula).

## GRUP 4 — AGENT ÇARPANLARI

C39 [D] Subagent kendi sistem promptu/araç setiyle sıfırdan başlar, parent cache'ini okumaz. → B8.
C40 [D] Subagent'lar oturum modelini devralır; Opus'a geçince hepsi Opus olur. → basit subagent için model: haiku.
C41 [D] Dynamic workflow ve fan-out'ta her ajan kendi isteklerini üstüne ekler. → /usage attribution'daki subagent payı.
C42 [D] Agent teams plan modunda ~7x token; teammate çıkana kadar tüketir (varsayılan kapalı; CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 ile açılır). → küçük takım, iş bitince kapat.
C43 [D] Opus'un varsayılan model olarak unutulması beklenmedik yüksek harcamanın tipik sebebi. → model-routing.md, /model.

## GRUP 5 — DÜŞÜNME VE ÇIKTI

C44 [D] Extended thinking varsayılan açık; token'lar çıktı fiyatıyla faturalanır; Opus 5.5/Sonnet 5.5/Haiku 5.5/Fable'da kapatılamaz; adaptive modeller sıfırdan farklı MAX_THINKING_TOKENS'ı yok sayar → /effort kullan. → basit işte effort düşür (başta, ortada değil: C20).
C45 [D] Thinking token'ları ekranda görünmez/özetlenebilir ama faturalanır. → C44.

## GRUP 6 — İÇERIĞIN KENDISI

C46 [G] Read çıktısı satır numaralı (cat -n biçimi) gelir; her satıra ek token. → büyük dosyada offset/limit.
C47 [G] WebFetch sayfayı markdown'a çevirip küçük bir modelle özetletir (ek model çağrısı) ve 15 dk önbellekler. → dar prompt yaz, aynı URL'i tekrar çekme.
C48 [G] WebSearch "extended" modu standarttan birkaç kat pahalı. → varsayılan standard.
C49 [I] Görseller, PDF sayfaları ve notebook çıktıları token-ağırdır. → hata metnini yapıştır, ekran görüntüsü yerine.
C50 [R] Tool sonuçlarının (dosya okuma, grep, bash) bağlamın %60–80'ini doldurduğu iddia ediliyor (bir üçüncü taraf blog; doğrulanmadı). → asıl hedef yine tool çıktıları: Bölüm D.
