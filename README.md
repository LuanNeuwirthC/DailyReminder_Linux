<div align="center">
  <img src="logo.png" alt="Logo Daily Reminder" width="140">

  <h1>Daily Reminder</h1>
  
  <p>
    <b>Versão Linux</b> • Desenvolvido para Ztrax
  </p>

  <p>
    <a href="https://github.com/LuanNeuwirthC/DailyReminder_Linux/releases/tag/latest">
      <img src="https://img.shields.io/badge/Download-Latest_Release-00D2FF?style=for-the-badge&logo=linux&logoColor=black" alt="Download">
    </a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/status-stable-green?style=flat-square">
    <img src="https://img.shields.io/badge/versão-1.0.7-blue?style=flat-square">
  </p>
</div>

<br>


> Ferramenta oficial de lembretes diários para a equipe de Desenvolvimento de Software da **Ztrax**.

O **Daily Reminder** é uma aplicação nativa e leve, desenvolvida para garantir que nenhum registro de daily seja esquecido. Com uma interface moderna em **PyQt6**, ele se integra perfeitamente ao ambiente de trabalho Linux (Gnome/Pop!_OS/Mint), rodando silenciosamente na bandeja do sistema.

---

##  Funcionalidades Principais

* **UI Cyberpunk/Neon**: Interface moderna em modo escuro com detalhes em azul neon, projetada para não cansar a vista.
* **Agendamento Preciso**: Defina seu horário de daily e o aplicativo cuidará do resto, rodando em segundo plano.
* **Auto-Start Integrado**: Opção nativa para iniciar junto com o sistema operacional.
* **Modo Tray (Bandeja)**: O app fica minimizado discretamente na barra superior (perto do relógio/WiFi).
* **Fluxo Automatizado**:
    1.  O alerta dispara no horário configurado.
    2.  Ao clicar em **"Registrar Daily"**, o navegador abre automaticamente em [rifyt.com/login](https://rifyt.com/login).
* **rapidez Verificação de Conclusão**:
    * Após o redirecionamento, o app exibe um pop-up de confirmação.
    * ✅ **SIM**: O app volta a dormir até o próximo dia.
    * ❌ **NÃO**: O app reabre a página de registros imediatamente para garantir a tarefa.

---

## 📦 Instalação (Usuário Final)

Não é necessário configurar Python ou compilar código. Utilizamos instaladores nativos `.deb`.

1. Acesse a aba **[Releases](../../releases)** deste repositório.
2. Baixe o arquivo `.zip` da versão mais recente (ex: `dailyreminder_installer_v7.zip`).
3. Abra seu terminal na pasta do download e execute:

```bash
# 1. Extraia o arquivo (substitua pelo nome do arquivo baixado)
unzip dailyreminder_installer_*.zip

# 2. Instale (O apt baixará automaticamente as dependências necessárias)
sudo apt install ./DailyReminder_*.deb

```
> Nota: Após a instalação, procure por "Daily Reminder" no menu de aplicativos do seu sistema.

# 🛠️ Stack Tecnológico
Projeto construído com tecnologias robustas para garantir compatibilidade e performance:
Tecnologia         Função
Python 3.10+       Linguagem Core
PyQt6Interface     Gráfica (GUI) moderna
SQLite             Banco de dados local
PyInstaller        Compilação de Binários
GitHub Actions     CI/CD para geração automática de pacotes .deb



<p align="center"> Desenvolvido por Luan Neuwirth para <b>Ztrax</b>. </p>
