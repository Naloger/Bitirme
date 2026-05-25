Bilgi toplama sürecini simüle eder. Dış dünyadan ham veri akışını (Se — Extraverted Sensing) ve olasılıkları (Ne — Extraverted Intuition) tarayarak sistemin "gözlem" yeteneğini oluşturur. İçsel olarak, geçmiş deneyimlerden örüntü çıkarımı (Si — Introverted Sensing, Ni — Introverted Intuition) yapar.

---

Collector Agent


Veriyi gürültüden arındıralım ve structured bir şekile dönüştürmeye çalışalım

Pre-process , process ve post-process yapalım

Noisy channel

Sinyal/Gürültü (S/N) Filtresi
Ajan, kendi iç durumunu veya sürekli akan dış veriyi her saniye kaydetmemelidir. Verinin "sürpriz" değeri yüksek olmalıdır.
Uygulama (İç Veri): İstatistiksel anomali tespiti (örneğin Isolation Forest algoritması). Sistem  iç loglarda sadece standart sapmanın dışına çıkılan anları yüksek olarak algılar.Uygulama (Dış Veri): Gelen metin Embedding'e dönüştürülür. Son 5 dakikadaki verilerle Cosine Similarity (Kosinüs Benzerliği) hesaplanır. Benzerlik %95'in üzerindeyse entropi düşüktür (Veri sıradandır, reddedilir).


Ajan, entropisi yüksek (yeni ve şaşırtıcı) bir veri yakaladığında, bunun "gerçekten anlamlı" bir bilgi mi yoksa sadece gürültülü bir kaos mu olduğunu anlamalıdır.


Ajanın nihai amacı izole veriler tutmak değil, dünyayı anlamlandırmaktır.
Uygulama: LLM, yeni veriden "Varlıklar" (Entities) ve "İlişkiler" (Relationships) çıkarır. (Örn: [Şirket_A] --(Satın_Aldı)--> [Şirket_B]).
Mantık: Bu varlıklar Neo4j'ye yazılır. Aynı ilişki veya varlıklar tekrar tekrar görüldüğünde, aralarındaki bağın weight (ağırlık) parametresi artırılır. Zamanla ağırlığı düşük olan bağlar budanır (Pruning), yüksek olanlar ise sistemin temel "Gerçekleri" (Ground Truth) haline gelir.

Bu mimari ile oluşturulan bir ajan, sonsuz veri akışı içinde boğulmaz; sadece istatistiksel ve mantıksal olarak "değerli" olan veriyi ayıklar, depolar ve ilişkilendirir

entropy based git-like tree creation

wiki like page yapılarıyla ilgili olaylar burda
content delta

Bilgi toplama sürecini simüle eder. Dış dünyadan ham veri akışını (Se — Extraverted Sensing) ve olasılıkları (Ne — Extraverted Intuition) tarayarak sistemin "gözlem" yeteneğini oluşturur. İçsel olarak, geçmiş deneyimlerden örüntü çıkarımı (Si — Introverted Sensing, Ni — Introverted Intuition) yapar.

---


| Modül | Açıklama | Ajan Karşılığı |
|-------|----------|----------------|
| **Query Decomposition (QD)** | Karmaşık sorguyu atomik alt-sorgulara parçalar | Collector Agent |
| **Context Refinement (CR)** | Alakasız bilgileri filtreler | Reflector Agent |
| **Query Grounding (QG)** | Önceki cevaplarla sorguyu zenginleştirir | Reflector Agent |
| **Logic Drafting (LD)** | Kanıtları mantıksal bir zincire dönüştürür | Organizer Agent |
| **Evidence Verification (EV)** | Kanıtların yeterliliğini kontrol eder | Reflector Agent |
| **Query Expansion (QE)** | Eksik kanıtlar için yeni sorgular üretir | Collector Agent |


---

- Collector Agent → Ham veri ve belgeleri toplar
- Organizer Agent → Graf yapısını oluşturur, Louvain ile kümeler
- Reflector Agent → Tutarsızlıkları tespit eder, güven hesaplar
- Grader → LLM ile belge alaka değerlendirmesi yapar
- Integrator Agent → Nihai yanıtı üretir
- Bu entegrasyon, Jung'un "bilinçdışı verinin bilince entegrasyonu" sürecini taklit eder:

- Shadow (Gölge): Yüksek prediction error → Alakasız/Tutarsız veri
- Persona: Organizasyon ve indeksleme
- Self: Nihai entegrasyon ve yanıt

---

Jung'un Algılama (Perception S/N) fonksiyonlarını implement eder.
- Extraverted Sensing (Se): Dış dünyadan ham veri akışı
- Introverted Sensing (Si): Geçmiş deneyimlerden örüntü çıkarımı
- Extraverted Intuition (Ne): Olasılık tarama
- Introverted Intuition (Ni): İçsel örüntü tanıma