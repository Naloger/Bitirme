# Bitirme Projesi

Yapay zekâ destekli bilişsel ajanlar, bilgi grafı (Knowledge Graph) ve doğal dil işleme bileşenlerini bir araya getiren modüler bir **full-stack** bitirme projesidir.

Proje; **Backend**, **Frontend** ve **Services** katmanlarından oluşur. Backend bilgi grafı, NLP ve veri katmanını sağlarken, Services katmanı bilişsel ajan mimarisini ve LLM orkestrasyonunu yürütür. Frontend ise sistemi gerçek zamanlı olarak gözlemleyebileceğiniz sohbet arayüzünü sunar.

[![Izle](https://download.githubusercontent.com/Naloger/Bitirme/blob/master/thumbnail.png)](https://github.com/Naloger/Bitirme/blob/master/Bitirme.webm?download=true)


---

# Genel Mimari

```
                        Kullanıcı
                            │
                            ▼
                   Frontend (Chat UI)
                            │
                            ▼
                  Services (AI Agents)
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
     REST API             MCP               Kafka
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ▼
                       Backend
                            │
     ┌──────────────┬──────────────┬──────────────┐
     ▼              ▼              ▼
  SQLite       Apache AGE      Typesense[Hazır Değil]        Kafka[Hazır Değil]
```

---

# Proje Yapısı

```
Bitirme/
│
├── backend/
│   ├── api/
│   ├── database/
│   ├── Libs/
│   ├── MCP/
│   ├── Scripts/
│   └── data/
│
├── frontend/
│   ├── static/
│   ├── templates/
│   └── app.py
│
├── services/
│   ├── Agents/
│   ├── ExecutiveControl/
│   ├── DefaultMode/
│   ├── Salience/
│   └── Sandbox/
│
├── startup.bat
├── shutdown.bat
├── pyproject.toml
└── README.md
```

---

# Bileşenler

## Backend

Backend katmanı sistemin veri işleme ve bilgi yönetim merkezidir.

Başlıca görevleri:

* Çok dilli metin işleme
* Lemmatizasyon (Türkçe / İngilizce)
* PPMI matrisi oluşturma
* Leiden Community Detection
* Spreading Activation
* Knowledge Graph yönetimi
* Apache AGE entegrasyonu
* Typesense indeksleme
* REST API
* MCP Server

Kullanılan teknolojiler

* Python 3.12+
* FastAPI
* SQLModel
* SQLite
* Apache AGE
* Typesense
* spaCy
* Stanza
* NumPy
* SciPy
* igraph
* leidenalg

---

## Services

Services katmanı bilişsel ajan mimarisini çalıştırır.

Temel bileşenleri:

* Salience Router
* Executive Control Network
* Default Mode Network
* Intent Agent
* Wikifier Agent
* Quad RDF Agent
* Sandbox Environment
* Memory Management
* Tool Calling
* MCP Client

Sistem LangGraph tabanlı durum makineleri kullanır.

İstekler önce Salience Router tarafından değerlendirilir ve uygun bilişsel moda yönlendirilir.

```
User Input
      │
      ▼
 Salience Router
      │
 ┌────┴─────┐
 ▼          ▼
Executive  Default
 Control     Mode
```

Executive Control Mode:

* görev yürütme
* araç kullanımı
* Python çalıştırma
* Shell
* Web Search
* dosya işlemleri

Default Mode:

* bilgi grafı düzenleme
* RDF Quad yönetimi
* topluluk analizi
* ontoloji oluşturma
* bilgi bütünleştirme

---

## Frontend

Frontend geliştiriciler için hazırlanmış gerçek zamanlı sohbet arayüzüdür.

Özellikleri

* gerçek zamanlı NDJSON stream
* LangGraph node'larını canlı izleme
* agent reasoning görüntüleme
* sohbet geçmişi
* çoklu konuşma desteği
* modern tek sayfa uygulaması
* FastAPI Proxy
* Vanilla JavaScript
* Glassmorphism tabanlı arayüz

Frontend doğrudan Backend'e bağlanmaz.

```
Browser
     │
     ▼
Frontend Proxy
     │
     ▼
Services API
```

Bu yapı CORS problemlerini ortadan kaldırır ve dağıtımı kolaylaştırır.

---

# Kullanılan Teknolojiler

## Backend

* Python
* FastAPI
* SQLModel
* SQLite
* Apache AGE
* Typesense
* spaCy
* Stanza
* NumPy
* SciPy
* igraph
* leidenalg

## Services

* LangGraph
* Instructor
* Pydantic AI
* OpenAI Compatible API
* Ollama
* MCP
* SQLite

## Frontend

* FastAPI
* HTML5
* CSS3
* Vanilla JavaScript
* httpx

## Altyapı

* uv
* Podman / Docker Compose
* Kafka
* Apache AGE
* Typesense

---

# Başlatma

Projeyi başlatmak için:

```bat
startup.bat
```

Projeyi durdurmak için:

```bat
shutdown.bat
```

---

# Python Ortamı

Projenin tüm bileşenleri **Python** ile geliştirilmiştir.

Bağımlılık yönetimi için **uv** kullanılmaktadır.


---

# Temel Özellikler

* Çok dilli NLP
* Knowledge Graph
* RDF Quad Store
* LangGraph Agent Architecture
* Salience Routing
* Executive Control Network
* Default Mode Network
* MCP (Model Context Protocol)
* Apache AGE Graph Database
* Typesense Search
* Community Detection
* PPMI Matrix
* Spreading Activation
* Tool Calling
* Sandbox Execution
* Streaming Chat UI
* FastAPI REST API
* Kafka destekli servis iletişimi

---

# Projenin Amacı

Bu proje, büyük dil modellerini yalnızca metin üreten sistemler olarak değil; dikkat (Salience), yürütücü kontrol (Executive Control), varsayılan ağ (Default Mode), bellek ve bilgi grafı gibi bilişsel kavramları temel alan modüler bir ajan mimarisi içerisinde çalıştırmayı amaçlamaktadır.

Uzun vadeli hedef, bilgi grafı tabanlı hafızaya sahip, araç kullanabilen, görev planlayabilen ve kendi bilgi tabanını sürekli güncelleyebilen bilişsel yapay zekâ ajanlarının geliştirilmesidir.
