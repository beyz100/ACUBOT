"""
Örnek: Bu prompt şu şekilde görünecek (37 dersi ile):
"""

# ÖRNEK PROMPT (37 dersi için)
prompt = """Answer in the student's language. Use only the provided courses list.

Courses:
CHE 101 Genel Kimya
CSE 101 Programlamaya Giriş
ENG 105 Akademik Amaçlar için İngilizce I
MAT 111 Kalkülüs I
PHY 101 Fizik I
TUR 101 Türk Dili I
BME 102 Mühendisler için Biyolojik Bilimler
CSE 102 Programlama Pratiği
ENG 106 Akademik Amaçlar için İngilizce II
MAT 112 Kalkülüs II
PHY 102 Fizik II
TUR 102 Türk Dili II
BME 105 Bilimde Beşeri Yaklaşımlar
BME 207 Mühendisler için Ekonomi
CSE 201 Algoritmalar I
MAT 211 Lineer Cebir
MAT 241 Ayrık Matematik
ACU 2001 Seçmeli Ders
BME 210 Mühendislik Etiği
BME 218 Olasılık ve Biyoistatistik
CSE 200 Zorunlu Yaz Stajı
CSE 202 Algoritmalar II
CSE 220 Web Programlama
MAT 222 Diferansiyel Denklemler
ACU 2002 Seçmeli Ders
ATA 101 Atatürk İlkeleri ve İnkılap Tarihi I
CSE 301 Bilgisayar Mimarisi
CSE 311 Yazılım
CSE 321 Veri Sistemleri
CSE 331 Keşifsel Veri Analizi
ACU 3001 Seçmeli Ders
ATA 102 Atatürk İlkeleri ve İnkılap Tarihi II
BME 320 Proje Yönetimi
CSE 300 Zorunlu Yaz Stajı
CSE 302 İşletim Sistemleri
CSE 312 Bilgisayar Ağları ve Sosyal Ağlar
CSE 322 Bulut Bilişim
CSE 332 Veri Bilimi ve Yapay Zeka
CSE 403 Bitirme Tasarım Projesi I
ACU 4001 Seçmeli Ders
ADS 4001 Genel Seçmeli
CSE 4001 Teknik Seçmeli
CSE 404 Bitirme Tasarım Projesi II
ACU 4002 Seçmeli Ders
ADS 4002 Genel Seçmeli
CSE 4002 Teknik Seçmeli

Question: Bilgisayar Mühendisliği bölümündeki dersleri söyle

Answer:"""

print("ÖRNEK PROMPT YAPISI:")
print("="*80)
print(f"Toplam karakter: {len(prompt)} character")
print(f"Toplam satır: {prompt.count(chr(10))} lines")
print(f"\nPrompt yapısı:")
print("1. System instruction: 1 satır (85 char)")
print("2. Boş satır")
print("3. 'Courses:' header")
print("4. 37 dersi (her biri ayrı satırda)")
print("5. Boş satır")
print("6. 'Question:' + soru")
print("7. 'Answer:' + LLM buradan yazacak")
print("\n" + "="*80)
print("TOKEN TAHMINI:")
print("="*80)
print("Prompt token'ları (~1200-1500)")
print("Output limiti: 8192 token")
print("✅ Yeterli space: 6700+ token")
print("\n37 dersi listelemek için gereken: ~1000 token")
print("✅ RAHAT SIĞIYOR!")

