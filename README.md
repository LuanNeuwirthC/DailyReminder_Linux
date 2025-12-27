# Daily Reminder para Linux 🕒🔵

Um lembrete diário leve e moderno desenvolvido em Python com PyQt6 para a equipe de Desenvolvimento de Software da empresa **Ztrax**. Ideal para não esquecer de registrar suas atividades diárias.

## ✨ Funcionalidades
- **Visual Moderno**: Interface em tons de azul neon e modo escuro.
- **Agendamento Inteligente**: Configure o horário que deseja ser lembrado e o app cuidará do resto.
- **Auto-start**: Opção de iniciar automaticamente com o sistema.
- **Sistema de Bandeja (Tray)**: Fica minimizado de forma discreta perto do relógio do sistema.
- **Redirecionamento**: Ao clicar em "Registrar Daily", você é automaticamente redirecionado para o site [https://rifyt.com/login](https://rifyt.com/login).
- **Confirmação**: Depois de um tempo, é enviado um novo aviso de confirmação.

## 🚀 Como Instalar (Como Usuário Final)
Para instalar o aplicativo no seu Linux (Debian/Ubuntu/Mint), abra o seu terminal na pasta onde baixou o arquivo e execute:

```bash
cd ~/Downloads
sudo dpkg -i dailyreminder_1.0.4_amd64.deb
sudo apt install -f
```

## 🛠️ Tecnologias
- Python 3
- PyQt6 (Interface Gráfica)
- SQLite (Armazenamento de configurações)
- PyInstaller (Empacotamento)
