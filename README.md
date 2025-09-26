# TradingView Webhook Bot for Binance

This project is a sophisticated, automated trading bot that connects TradingView alerts to the Binance Futures platform. It operates via webhooks, allowing for instant, automated trade execution based on your custom TradingView strategies. The bot is managed and monitored through a Telegram interface, providing a seamless user experience.

## 1. Project Description

The primary goal of this bot is to bridge the gap between TradingView's powerful charting and alert system and Binance's high-liquidity futures market. By listening for webhook signals from your TradingView alerts, the bot can execute market orders (long or short, open or close) on your behalf. It includes a robust backend service layer for interacting with Binance, a data model for managing settings, orders, and logs, and a Telegram bot interface for command, control, and real-time notifications.

### Key Features:
- **TradingView Integration**: Receives and processes webhook alerts from TradingView for automated strategy execution.
- **Binance Futures**: Connects to Binance Futures (or Testnet) to open and close positions.
- **Telegram Control**: A fully functional Telegram bot interface to start, monitor, and control the bot's operations.
- **Risk Management**: Includes logic for calculating order quantities based on a percentage of your balance and respects Binance's trading limits (min/max quantity, step size, etc.).
- **Persistent Storage**: Uses JSON files to manage settings, logs, alerts, and order history.
- **Secure and Self-Hosted**: You have full control over the bot by hosting it on your own server.

---

## 2. How to Download

You can download or clone the project from the official GitHub repository.

```bash
git clone https://github.com/beydah/TradingView-Webhook-Bot.git
cd TradingView-Webhook-Bot
```

---

## 3. Installation and Setup Guide

Setting up this bot requires a server that is publicly accessible on the internet to receive webhooks from TradingView. A Virtual Private Server (VPS) is the recommended solution.

### Step 1: Get a Hosting Server (VPS)
1.  **Choose a Provider**: Select a VPS provider such as [DigitalOcean](https://www.digitalocean.com/), [Linode](https://www.linode.com/), [Vultr](https://www.vultr.com/), or AWS EC2.
2.  **Select an OS**: A Linux distribution like **Ubuntu 22.04 LTS** is recommended.
3.  **Server Size**: A basic, low-cost server is usually sufficient to run the bot.
4.  **Access Your Server**: Connect to your server via SSH using the provided credentials.
    ```bash
    ssh root@YOUR_SERVER_IP
    ```

### Step 2: Set Up a Python Virtual Environment
1.  **Install Python and venv**:
    ```bash
    sudo apt update
    sudo apt install python3-pip python3-venv
    ```
2.  **Create a Project Directory**: Clone the repository (as shown in the download section) or upload the project files to a directory (e.g., `/var/www/trading-bot`).
3.  **Create the Virtual Environment**:
    ```bash
    cd /path/to/your/project
    python3 -m venv venv
    ```
4.  **Activate the Environment**:
    ```bash
    source venv/bin/activate
    ```
    Your terminal prompt should now be prefixed with `(venv)`.

### Step 3: Get a Domain and Configure DNS
1.  **Purchase a Domain**: Buy a domain name from a registrar like [Namecheap](https://www.namecheap.com/) or [GoDaddy](https://www.godaddy.com/).
2.  **Configure DNS**: In your domain registrar's DNS management panel, create an **A Record** that points your domain (or a subdomain like `bot.yourdomain.com`) to your server's public IP address.

### Step 4: Install and Configure Nginx
Nginx will act as a reverse proxy, forwarding incoming webhook requests to the bot's web server.

1.  **Install Nginx**:
    ```bash
    sudo apt install nginx
    ```
2.  **Create an Nginx Configuration File**:
    ```bash
    sudo nano /etc/nginx/sites-available/tradingbot
    ```
3.  **Paste the Following Configuration**: Replace `your_domain.com` with your actual domain.
    ```nginx
    server {
        listen 80;
        server_name your_domain.com;

        location / {
            proxy_pass http://127.0.0.1:5001;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
    ```
4.  **Enable the Configuration**:
    ```bash
    sudo ln -s /etc/nginx/sites-available/tradingbot /etc/nginx/sites-enabled/
    sudo nginx -t # Test for syntax errors
    sudo systemctl restart nginx
    ```

### Step 5: Secure with SSL (Certbot)
1.  **Install Certbot**:
    ```bash
    sudo apt install certbot python3-certbot-nginx
    ```
2.  **Obtain the SSL Certificate**: Certbot will automatically detect your domain from the Nginx config, obtain a certificate, and configure Nginx for HTTPS.
    ```bash
    sudo certbot --nginx -d your_domain.com
    ```
    Follow the on-screen prompts. Choose to redirect HTTP traffic to HTTPS.
3.  **Verify Auto-Renewal**: Certbot automatically sets up a cron job for renewal. You can test it with:
    ```bash
    sudo certbot renew --dry-run
    ```

### Step 6: Obtain API Keys and Credentials
1.  **Telegram**: 
    - Talk to `@BotFather` on Telegram to create a new bot. Save the **Bot Token**.
    - Talk to `@userinfobot` to get your personal **Telegram User ID**.
2.  **Binance**: 
    - For testing, create API keys on the [Binance Testnet](https://testnet.binancefuture.com/).
    - For live trading, create API keys from your main Binance account under API Management. Ensure you enable Futures trading permissions.
    - **IMPORTANT**: For security, restrict API key access to your server's IP address only.

### Step 7: Configure and Run the Bot
1.  **Fill in Settings**: The bot creates a settings file at `e_database/db_a_settings.json` on its first run. You need to manually populate this file with all the credentials you obtained.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Bot**:
    ```bash
    python3 main.py
    ```
    To keep the bot running permanently, use a process manager like `systemd` or `supervisor`.

---

## 4. File Structure and Code Documentation

The project is organized into a service layer, a data model layer, and a database layer.

-   `main.py`: The main entry point of the application. It initializes and starts the TradingView and Telegram service threads.

-   **`c_service/` (Service Layer)**
    -   `sr_a_trade.py`: Contains the core business logic for executing trades. It calculates quantities and leverage, validates them against Binance rules, and handles the process of opening/closing positions.
    -   `sr_b_tradingview.py`: Runs a Flask web server (using Waitress) to listen for incoming webhook calls from TradingView. It validates, parses, and queues the alerts.
    -   `sr_c_binance.py`: A dedicated service module for all interactions with the Binance Futures API (fetching wallet info, symbol data, market prices, placing orders, etc.).
    -   `sr_d_transaction.py`: Manages user state and processes commands received from the Telegram bot.
    -   `sr_e_telegram.py`: A service module for sending messages, buttons, and documents via the Telegram Bot API.

-   **`d_model/` (Data Model Layer)**
    -   `md_a_settings.py`: Manages the application's configuration, such as API keys and webhook settings.
    -   `md_c_alerts.py`: Manages the queue of incoming trading alerts from TradingView.
    -   `md_d_orders.py`: Manages the history of opened and closed orders.
    -   `md_e_logs.py`: Manages the logging of events, errors, and transactions.

-   **`e_database/`**
    - This directory stores the JSON files that act as a simple database for settings, alerts, orders, and logs.

---

## 5. How to Contribute

Contributions are welcome! If you'd like to contribute to the project, please follow these steps:

1.  **Fork the Repository**: Create your own fork of the project.
2.  **Create a Branch**: Make your changes in a dedicated branch.
    ```bash
    git checkout -b my-new-feature
    ```
3.  **Commit Your Changes**: Write clear and concise commit messages.
    ```bash
    git commit -am 'Add some amazing feature'
    ```
4.  **Push to the Branch**:
    ```bash
    git push origin my-new-feature
    ```
5.  **Open a Pull Request**: Submit a pull request from your fork to the main repository. Please provide a detailed description of the changes you've made.

If you find a bug or have a feature request, please open an issue on the GitHub repository page.
