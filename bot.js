const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const PYTHON_WEBHOOK_URL = 'http://127.0.0.1:8000/webhook';

// Mapa em memória para associar o número do usuário ao seu ID interno original do WhatsApp
const userMap = new Map();

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', (qr) => {
    console.log('Escaneie o QR Code abaixo com o seu WhatsApp:');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ Bot do WhatsApp conectado com sucesso!');
});

// 1. RECEBE MENSAGEM DO WHATSAPP -> REPASSA PARA O PYTHON
client.on('message', async (msg) => {
    // Ignora mensagens de grupos ou enviadas por você mesmo
    if (msg.from.includes('@g.us') || msg.fromMe) return;

    try {
        // Pega os dados detalhados do contato
        const contact = await msg.getContact();
        const realNumber = contact.number || msg.from.split('@')[0];

        // 📌 BUSCA APENAS O NOME DA SUA AGENDA (sem usar pushname)
        const nomeSalvoAgenda = contact.name || contact.shortName || null;

        // Mapeia o número real para o ID exato que o WhatsApp espera
        userMap.set(realNumber, msg.from);

        // Envia para a API Python
        await axios.post(PYTHON_WEBHOOK_URL, {
            user_id: realNumber,
            text: msg.body,
            timestamp: msg.timestamp,
            pushName: nomeSalvoAgenda
        });
    } catch (error) {
        console.error('Erro ao repassar mensagem para o Python:', error.message);
    }
});

// 2. ROTA QUE O PYTHON CHAMA PARA RESPONDER AO WHATSAPP
app.post('/send-message', async (req, res) => {
    const { number, message, options } = req.body;

    try {
        const cleanNumber = number.toString().replace(/\D/g, '');
        const targetChatId = userMap.get(cleanNumber) || `${cleanNumber}@c.us`;

        let finalMessage = message;

        if (options && Array.isArray(options) && options.length > 0) {
            finalMessage += '\n\n';
            options.forEach((opt, index) => {
                finalMessage += `*${index + 1}* - ${opt}\n`;
            });
            finalMessage += '\n_Digite o número ou a opção desejada:_';
        }

        await client.sendMessage(targetChatId, finalMessage);
        console.log(`✉️ Mensagem enviada para ${cleanNumber}`);
        res.status(200).json({ status: 'sent' });

    } catch (error) {
        console.error('Erro detalhado ao responder cliente:', error.message);
        res.status(500).json({ error: error.message || error });
    }
});

app.listen(3000, () => {
    console.log('🚀 Microserviço Node.js rodando na porta 3000');
});

client.initialize();