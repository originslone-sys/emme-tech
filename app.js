// CONFIGURAÇÃO
const TOKEN_ADDRESS = "0x9be6b67b83fc593800780cb7794c29b569272bd1";
let STAKING_CONTRACT_ADDRESS = ""; // Você vai preencher

// ABI do Token (Simplificada)
const TOKEN_ABI = [
    {
        "constant": false,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
];

// ABI do Staking (Simplificada - mesma do contrato que você deployou)
const STAKING_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_stakingToken", "type": "address"}],
        "stateMutability": "nonpayable",
        "type": "constructor"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_amount", "type": "uint256"}],
        "name": "addRewardTokens",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "claim",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getCurrentAPY",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_user", "type": "address"}],
        "name": "getUserInfo",
        "outputs": [
            {"internalType": "uint256", "name": "stakedAmount", "type": "uint256"},
            {"internalType": "uint256", "name": "pendingRewards", "type": "uint256"},
            {"internalType": "uint256", "name": "lastStakeTime", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "_user", "type": "address"}],
        "name": "pendingReward",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_rewardPerSecond", "type": "uint256"}],
        "name": "setRewardPerSecond",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_amount", "type": "uint256"}],
        "name": "stake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "stakingToken",
        "outputs": [{"internalType": "contract IERC20", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalStaked",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "_amount", "type": "uint256"}],
        "name": "unstake",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
];

// Variáveis globais
let web3;
let stakingContract;
let tokenContract;
let userAccount;

// Elementos DOM
const elements = {
    statusText: () => document.getElementById('statusText'),
    walletAddress: () => document.getElementById('walletAddress'),
    network: () => document.getElementById('network'),
    stakedAmount: () => document.getElementById('stakedAmount'),
    pendingRewards: () => document.getElementById('pendingRewards'),
    lastStakeTime: () => document.getElementById('lastStakeTime'),
    stakingContractEl: () => document.getElementById('stakingContract'),
    currentAPY: () => document.getElementById('currentAPY'),
    txMessage: () => document.getElementById('txMessage'),
    txHash: () => document.getElementById('txHash'),
    txLink: () => document.getElementById('txLink'),
    txStatus: () => document.getElementById('transactionStatus')
};

// Inicialização
window.addEventListener('load', async () => {
    // Primeiro, peça ao usuário o endereço do contrato staking
    const savedAddress = localStorage.getItem('stakingContractAddress');
    if (savedAddress) {
        STAKING_CONTRACT_ADDRESS = savedAddress;
        elements.stakingContractEl().textContent = savedAddress.substring(0, 10) + '...';
    } else {
        const address = prompt("Cole o endereço do seu contrato staking (aquele que você deployou):");
        if (address && address.startsWith('0x') && address.length === 42) {
            STAKING_CONTRACT_ADDRESS = address;
            localStorage.setItem('stakingContractAddress', address);
            elements.stakingContractEl().textContent = address.substring(0, 10) + '...';
        } else {
            alert("Endereço inválido! Atualize a página e tente novamente.");
            return;
        }
    }
    
    // Verifica se MetaMask está instalado
    if (typeof window.ethereum !== 'undefined') {
        await initWeb3();
    } else {
        elements.statusText().textContent = "Instale o MetaMask!";
        elements.statusText().className = "error";
    }
});

// Inicializa Web3
async function initWeb3() {
    try {
        web3 = new Web3(window.ethereum);
        
        // Solicita conexão da carteira
        const accounts = await window.ethereum.request({ 
            method: 'eth_requestAccounts' 
        });
        
        userAccount = accounts[0];
        
        // Inicializa contratos
        stakingContract = new web3.eth.Contract(STAKING_ABI, STAKING_CONTRACT_ADDRESS);
        tokenContract = new web3.eth.Contract(TOKEN_ABI, TOKEN_ADDRESS);
        
        // Atualiza interface
        updateConnectionInfo();
        updateStakeInfo();
        
        // Listeners para mudanças
        window.ethereum.on('accountsChanged', (accounts) => {
            userAccount = accounts[0];
            updateConnectionInfo();
            updateStakeInfo();
        });
        
        window.ethereum.on('chainChanged', () => {
            window.location.reload();
        });
        
    } catch (error) {
        console.error("Erro ao inicializar:", error);
        elements.statusText().textContent = "Erro: " + error.message;
        elements.statusText().className = "error";
    }
}

// Conecta carteira manualmente
async function connectWallet() {
    if (!window.ethereum) {
        alert("Por favor, instale o MetaMask!");
        return;
    }
    
    try {
        await initWeb3();
    } catch (error) {
        alert("Erro ao conectar: " + error.message);
    }
}

// Atualiza informações de conexão
function updateConnectionInfo() {
    if (userAccount) {
        elements.statusText().textContent = "Conectado";
        elements.statusText().className = "success";
        elements.walletAddress().textContent = 
            userAccount.substring(0, 6) + '...' + userAccount.substring(38);
        
        // Detecta rede
        const chainId = window.ethereum.chainId;
        elements.network().textContent = chainId === '0x89' ? 'Polygon' : 'Outra Rede';
    }
}

// Atualiza informações do stake
async function updateStakeInfo() {
    if (!stakingContract || !userAccount) return;
    
    try {
        const info = await stakingContract.methods.getUserInfo(userAccount).call();
        const apy = await stakingContract.methods.getCurrentAPY().call();
        
        // Formata valores
        const staked = web3.utils.fromWei(info.stakedAmount, 'ether');
        const pending = web3.utils.fromWei(info.pendingRewards, 'ether');
        const apyPercent = web3.utils.fromWei(apy, 'ether');
        
        elements.stakedAmount().textContent = parseFloat(staked).toFixed(4);
        elements.pendingRewards().textContent = parseFloat(pending).toFixed(4);
        elements.currentAPY().textContent = parseFloat(apyPercent).toFixed(2) + "%";
        
        // Formata data
        if (info.lastStakeTime > 0) {
            const date = new Date(info.lastStakeTime * 1000);
            elements.lastStakeTime().textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }
        
    } catch (error) {
        console.error("Erro ao buscar info:", error);
    }
}

// Aprova e faz stake
async function approveAndStake() {
    const amountInput = document.getElementById('stakeAmount');
    const amount = amountInput.value;
    
    if (!amount || amount <= 0) {
        alert("Digite uma quantidade válida!");
        return;
    }
    
    showTransactionStatus("Iniciando aprovação...");
    
    try {
        const amountWei = web3.utils.toWei(amount, 'ether');
        
        // 1. Aprovação
        showTransactionStatus("Aprovando tokens...");
        const approveTx = await tokenContract.methods.approve(STAKING_CONTRACT_ADDRESS, amountWei)
            .send({ from: userAccount });
        
        showTransactionStatus("Aprovação confirmada! Fazendo stake...", approveTx.transactionHash);
        
        // 2. Stake
        const stakeTx = await stakingContract.methods.stake(amountWei)
            .send({ from: userAccount });
        
        showTransactionStatus("Stake realizado com sucesso!", stakeTx.transactionHash);
        
        // Limpa input e atualiza
        amountInput.value = '';
        setTimeout(updateStakeInfo, 3000);
        
    } catch (error) {
        showTransactionStatus("Erro: " + error.message);
        console.error(error);
    }
}

// Claim rewards
async function claimRewards() {
    showTransactionStatus("Processando claim...");
    
    try {
        const tx = await stakingContract.methods.claim()
            .send({ from: userAccount });
        
        showTransactionStatus("Rewards resgatados com sucesso!", tx.transactionHash);
        setTimeout(updateStakeInfo, 3000);
        
    } catch (error) {
        showTransactionStatus("Erro: " + error.message);
    }
}

// Unstake tudo
async function unstakeAll() {
    if (!confirm("Tem certeza que deseja fazer unstake de todos os tokens?")) return;
    
    showTransactionStatus("Obtendo informações para unstake...");
    
    try {
        const info = await stakingContract.methods.getUserInfo(userAccount).call();
        
        if (info.stakedAmount === '0') {
            alert("Você não tem tokens em stake!");
            hideTransactionStatus();
            return;
        }
        
        showTransactionStatus("Processando unstake...");
        const tx = await stakingContract.methods.unstake(info.stakedAmount)
            .send({ from: userAccount });
        
        showTransactionStatus("Unstake realizado com sucesso!", tx.transactionHash);
        setTimeout(updateStakeInfo, 3000);
        
    } catch (error) {
        showTransactionStatus("Erro: " + error.message);
    }
}

// Atualiza endereço do contrato
function updateContractAddress() {
    const customAddress = document.getElementById('customStakingContract').value;
    
    if (customAddress && customAddress.startsWith('0x') && customAddress.length === 42) {
        STAKING_CONTRACT_ADDRESS = customAddress;
        localStorage.setItem('stakingContractAddress', customAddress);
        elements.stakingContractEl().textContent = customAddress.substring(0, 10) + '...';
        
        // Recarrega contratos
        stakingContract = new web3.eth.Contract(STAKING_ABI, STAKING_CONTRACT_ADDRESS);
        updateStakeInfo();
        
        alert("Contrato atualizado!");
    } else {
        alert("Endereço inválido!");
    }
}

// Mostra status da transação
function showTransactionStatus(message, hash = null) {
    elements.txStatus().style.display = 'block';
    elements.txMessage().textContent = message;
    
    if (hash) {
        elements.txHash().textContent = "Hash: " + hash.substring(0, 20) + '...';
        elements.txLink().href = `https://polygonscan.com/tx/${hash}`;
        elements.txLink().style.display = 'block';
        
        // Esconde após 15 segundos
        setTimeout(hideTransactionStatus, 15000);
    } else {
        elements.txHash().textContent = "";
        elements.txLink().style.display = 'none';
    }
}

// Esconde status da transação
function hideTransactionStatus() {
    elements.txStatus().style.display = 'none';
}
