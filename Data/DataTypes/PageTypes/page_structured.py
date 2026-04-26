import time
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

from Data.DataTypes.PageTypes.page import Page


# --- Yardımcı Veri Modelleri ---


class CustomTriple(BaseModel):
    """Geliştirilmiş RDF Üçlüsü (Özne - Yüklem - Nesne)"""

    subject: str
    object_: str
    weight: float = 0.0


class Section(BaseModel):
    """Wikipedia'daki alt başlıkları temsil eder."""

    title: str
    content: str
    level: int = 2  # Başlık seviyesi (H2, H3 vb.)


class Reference(BaseModel):
    """Wikipedia tarzı kaynakça/referans yönetimi."""

    source_url_or_id: str
    description: Optional[str] = None
    accessed_at: float = Field(default_factory=time.time)


# --- Ana Sınıf ---


class StructuredPage(Page):  # Page sınıfından miras aldığını varsayıyoruz
    """
    Organize edilmiş bilgi temsili (Evergreen Note).
    Wikipedia mimarisinden esinlenilmiş, RDF destekli genişletilebilir yapı.
    """

    # 1. TEMEL KİMLİK (Identity)
    title: str = "Untitled Concept"
    aliases: List[str] = Field(
        default_factory=list
    )  # Wikipedia "Redirects" / Eşanlamlılar
    description: str = "Untitled description"  # Wikipedia "Lead Paragraph" (Özet)

    # 2. YAPISAL İÇERİK (Content Structure)
    infobox: Dict[str, Any] = Field(
        default_factory=dict
    )  # Sayfanın sağındaki özet bilgi kutusu
    sections: List[Section] = Field(
        default_factory=list
    )  # Table of Contents / Alt başlıklar

    # 3. SEMANTİK VE BİLGİ AĞI (Semantic & Knowledge Graph)
    categories: Set[str] = Field(default_factory=list)  # Wikipedia kategorileri
    tags: Set[str] = Field(default_factory=list)  # Serbest etiketler
    links: Set[str] = Field(default_factory=set)  # Referans verilen sayfa ID'leri
    backlinks: Set[str] = Field(
        default_factory=set
    )  # Bu sayfaya referans veren sayfa ID'leri

    entities: List[str] = Field(
        default_factory=list
    )  # Metin içinden çıkarılmış varlıklar (NER)

    # Sayfa içi mantıksal harita (RDF tabanlı)
    structured_page_graph: List[CustomTriple] = Field(default_factory=list)
    related_pages: List[str] = Field(
        default_factory=list
    )  # Wikipedia "See Also" (Ayrıca Bakınız)

    # 4. KAYNAKÇA VE İZLEME (Provenance)
    references: List[Reference] = Field(default_factory=list)

    # 5. EVERGREEN METRİKLERİ (Lifecycle)
    revision_count: int = 0
    extracted_at: float = Field(default_factory=time.time)
    last_updated_at: float = Field(default_factory=time.time)

    def add_relation(self, subject: str, predicate: str, obj: str, weight: float = 1.0):
        """
        Grafiğe yeni bir RDF üçlüsü (ilişki) ekler ve sayfayı evrimleştirir.
        Örnek: add_relation("Machine Learning", "is_subfield_of", "Artificial Intelligence")
        """

    def add_infobox_item(self, key: str, value: Any):
        """Wikipedia tarzı bilgi kutusuna veri ekler."""
        self.infobox[key] = value
        self._bump_revision()

    def add_reference(self, url: str, description: str = ""):
        """Kavrama yeni bir kaynakça ekler."""
        self.references.append(Reference(source_url_or_id=url, description=description))
        self._bump_revision()

    def _bump_revision(self):
        """Evergreen prensibi: Bilgi değiştikçe revizyon ve tarih güncellenir."""
        self.revision_count += 1
        self.last_updated_at = time.time()
        # Eğer parent class'ta (Page) bir touch() metodu varsa burada çağrılabilir:
        if hasattr(super(), "touch"):
            super().touch()
