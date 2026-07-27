import sys
from PySide6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)
    from gui.app import create_app
    window = create_app()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
