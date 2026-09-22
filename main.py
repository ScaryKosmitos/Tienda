import base_datos as db
import interfaz

if __name__ == "__main__":
    db.inicializar_db()
    interfaz.iniciar_app()

    