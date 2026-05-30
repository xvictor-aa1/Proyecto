╔══════════════════════════════════════════════════════════════╗
║   SISTEMA DE RECEPCIÓN DE EQUIPOS v5.0 — MODO RED           ║
║   Coordinación de Informática · Alcaldía Carlos Arvelo       ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INSTALAR (solo la primera vez, en el equipo SERVIDOR)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1. Instalar Python desde: https://www.python.org/downloads/
     (marcar la opción "Add Python to PATH")

  2. Abrir CMD y ejecutar:
     pip install flask reportlab pillow

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ARRANCAR EL SERVIDOR (equipo principal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  → Doble clic en INICIAR.bat

  Verás una ventana negra (CMD) que dice:
  "Abrir en: http://localhost:5000"
  → NO CIERRES esa ventana negra mientras usas el sistema.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SABER LA IP DEL SERVIDOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  En el equipo servidor:
  1. Presiona Windows + R
  2. Escribe: cmd  → Enter
  3. Escribe: ipconfig  → Enter
  4. Busca "Dirección IPv4" — ejemplo: 192.168.1.15

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CONECTARSE DESDE OTROS EQUIPOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  En cualquier otro equipo de la misma red:
  → Abrir Chrome o Firefox
  → Escribir en la barra de direcciones:
     http://192.168.1.15:5000
     (reemplaza 192.168.1.15 con la IP real del servidor)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CLAVES DE ACCESO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Técnico     → Tecnico@2026
  Admin       → Admin@2026
  Super Admin → //super_admin

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 IMPORTANTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • El servidor (equipo principal) debe estar ENCENDIDO
    para que los demás puedan usar el sistema.
  • Todos los equipos deben estar en la MISMA red WiFi o cable.
  • La base de datos es única y compartida por todos.
  • Si el Firewall de Windows bloquea el acceso, ver abajo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SI OTROS EQUIPOS NO PUEDEN CONECTARSE (Firewall)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  En el equipo SERVIDOR:
  1. Buscar "Firewall de Windows" en el menú inicio
  2. Clic en "Configuración avanzada"
  3. "Reglas de entrada" → "Nueva regla"
  4. Tipo: Puerto → TCP → Puerto específico: 5000
  5. Permitir la conexión → Guardar
