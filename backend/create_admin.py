
import database
import security
import getpass
import sys

def create_super_user():
    print("=========================================")
    print("   TASK MANAGER - ADMIN OLUŞTURUCU 🛡️")
    print("=========================================")

    conn = database.get_db_connection()
    if conn is None:
        print("❌ HATA: Veritabanına bağlanılamadı. .env dosyanızı kontrol edin.")
        return

    try:
        email = input("Admin Email: ").strip()
        if not email:
            print("❌ Email boş olamaz.")
            return

        password = getpass.getpass("Şifre: ")
        if len(password) < 6:
            print("❌ Şifre en az 6 karakter olmalıdır.")
            return
            
        password_confirm = getpass.getpass("Şifre (Tekrar): ")
        if password != password_confirm:
            print("❌ Şifreler eşleşmiyor.")
            return

        name = input("İsim (Opsiyonel, Enter'a basarsan 'Admin' olur): ").strip()
        if not name:
            name = "System Admin"

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            print(f"\n⚠️  UYARI: '{email}' adresine sahip bir kullanıcı zaten var.")
            choice = input(f"Bu kullanıcının rolünü 'ADMIN' olarak güncellemek ister misiniz? (e/h): ").lower()
            
            if choice == 'e':
                cursor.execute("UPDATE users SET role = 'admin' WHERE email = %s", (email,))
                conn.commit()
                print(f"\n✅ BAŞARILI: '{email}' kullanıcısı ADMIN yetkisine yükseltildi.")
            else:
                print("\nİşlem iptal edildi.")
        
        else:
            hashed_password = security.get_password_hash(password)
            
            query = """
            INSERT INTO users (name, email, password, role) 
            VALUES (%s, %s, %s, 'admin')
            """
            cursor.execute(query, (name, email, hashed_password))
            conn.commit()
            
            print(f"\n✅ BAŞARILI: Yeni Admin kullanıcısı ('{email}') oluşturuldu.")

    except Exception as e:
        print(f"\n❌ BEKLENMEDİK HATA: {e}")
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if conn and conn.is_connected(): conn.close()

if __name__ == "__main__":
    create_super_user()