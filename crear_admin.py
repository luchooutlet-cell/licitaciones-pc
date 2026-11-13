from app import app
from models import db, Usuario

with app.app_context():
    db.create_all()

    user_existente = Usuario.query.filter_by(username="admin").first()
    if user_existente:
        db.session.delete(user_existente)
        db.session.commit()

    admin = Usuario(
        username="admin",
        nombre="Administrador",
        rol="admin"
    )
    admin.set_password("admin123")
    db.session.add(admin)
    db.session.commit()
    print("✅ Usuario 'admin' creado con contraseña 'admin123'")