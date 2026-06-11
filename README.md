# 🐕 Sistema de Detección de Ladridos con Frigate NVR

Este repositorio contiene la arquitectura, configuraciones y el microservicio puente para implementar un sistema inteligente de detección de ladridos de perro. El sistema procesa el audio en tiempo real utilizando Inteligencia Artificial, está optimizado para ejecutarse en un NAS **Synology DS225+** mediante Docker y se integra nativamente con **Surveillance Station** para el envío de notificaciones push.

## 📋 Índice
- [Esquema de la Arquitectura](#-esquema-de-la-arquitectura)
- [Cómo Funciona Paso a Paso](#-cómo-funciona-paso-a-paso)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Estructura de Archivos Clave](#-estructura-de-archivos-clave)
- [Configuración de Frigate (`config.yml`)](#-configuración-de-frigate-configyml)

---

## 🏗️ Esquema de la Arquitectura

El flujo de datos e integraciones del sistema se distribuye de la siguiente manera:

[ Cámara Tapo C210 ] (192.168.1.167)
│
│ (RTSP - Audio/Vídeo)
▼
================= SYNOLOGY DS225+ (Docker) =================
│                                                          │
│   [ go2rtc ] ──(Audio interno)──> [ Frigate v0.17.1 ]    │
│                                           │              │
│                                           │ (MQTT)       │
│                                           ▼              │
│   [ bridge.py ] <──(Suscribe)────── [ Mosquitto ]        │
│        │                             (Puerto 1883)       │
│        │                                                 │
=========│==================================================
│
│ (HTTP POST - Webhook)
▼
[ Surveillance Station ] (Puerto 5000)
│
│ (Push Notification)
▼
[ 📱 Aplicación móvil DS cam ]


---

## 🔄 Cómo Funciona Paso a Paso

1. **Emisión del Stream:** La cámara Tapo C210 transmite de forma continua audio y vídeo a través del protocolo RTSP (puerto 554) dentro de la red local.
2. **Gestión con go2rtc:** `go2rtc` (incluido dentro de Frigate) se conecta a la cámara y gestiona el stream de forma eficiente para evitar problemas de permisos de las cámaras Tapo.
3. **Análisis con IA:** Frigate extrae el audio del stream y lo procesa mediante un modelo de **TensorFlow Lite** entrenado para reconocer sonidos. Está configurado para escuchar específicamente ladridos de perro (`bark`) con un umbral de confianza del **80%**.
4. **Publicación del Evento:** Cuando detecta un ladrido, Frigate publica un mensaje en el topic `frigate/sala_tapo/audio/bark` del broker Mosquitto.
5. **Filtrado en el Puente:** El script en Python (`bridge.py`) está suscrito a ese topic, lee el mensaje e identifica que es un evento nuevo (`"type": "new"`). Tiene un cooldown de 10 segundos para evitar spam.
6. **Disparo del Webhook:** El puente hace una petición HTTP POST a la URL de Surveillance Station con el token de autenticación para que reciba la llamada y genere una notificación.
7. **Notificación Push:** La app DS cam recibe la notificación push de Surveillance Station y te avisa en tu móvil, estés donde estés.

---

## 🛠️ Tecnologías Utilizadas

| Componente | Tecnología | Descripción |
| :--- | :--- | :--- |
| **Detección de Audio** | **Frigate NVR** | Sistema de videovigilancia de código abierto especializado en detección de objetos y audio mediante IA. Usa TensorFlow Lite para clasificar sonidos en tiempo real. |
| **Gestión de Streams** | **go2rtc** | Servidor de streams multimedia integrado en Frigate. Gestiona la conexión RTSP con la cámara y resuelve problemas de compatibilidad con Tapo. |
| **Mensajería** | **Mosquitto (MQTT)** | Broker de mensajería ligero para dispositivos IoT. Actúa de "central de comunicaciones": Frigate le envía eventos y el puente Python los recibe. |
| **Integración** | **bridge.py (Python)** | Microservicio puente escrito en Python. Escucha el topic MQTT de ladridos y dispara el webhook de Surveillance Station. Pesa ~19MB de RAM y tiene reconexión automática. |
| **Notificaciones** | **Surveillance Station** | Sistema de gestión de cámaras de Synology. Recibe el webhook y envía la notificación push a la app DS cam en tu móvil. |
| **Infraestructura** | **Docker / Container Manager** | Plataforma de contenedores que ejecuta los tres servicios de forma aislada y fiable. Proporciona la interfaz gráfica para gestionarlos. |

---

## 📂 Estructura de Archivos Clave

* **`/volume1/docker/frigate/docker-compose.yml`**: Define y orquesta los tres contenedores: Frigate, Mosquitto y el puente. Es el archivo principal de la instalación.
* **`/volume1/docker/frigate/config/config.yml`**: Configuración de Frigate: qué cámara escuchar, qué sonidos detectar, umbral de confianza y conexión MQTT.
* **`/volume1/docker/frigate/mosquitto/mosquitto.conf`**: Configuración del broker MQTT: puerto, permisos de conexión anónima (red local) y persistencia de mensajes.
* **`/volume1/docker/frigate/bridge/bridge.py`**: Script Python del puente. Lee el topic MQTT y dispara el webhook de Surveillance Station con cooldown configurable.

---

## ⚙️ Configuración de Frigate (`config.yml`)

💡 ¿Por qué go2rtc?
Las cámaras Tapo tienen restricciones de autenticación RTSP que generan errores Operation not permitted cuando ffmpeg intenta conectarse directamente. go2rtc actúa como intermediario y resuelve este problema.

Documento generado originalmente el 9 de junio de 2026 · Sistema en producción en Synology DS225+.
