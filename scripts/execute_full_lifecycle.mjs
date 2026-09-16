import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createClient, createAccount } from '../../AetherDungeon/frontend/node_modules/genlayer-js/dist/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
    console.log("=====================================================================================");
    console.log("   ALPHATANK CAPITAL — EXECUTING COMPLETE REAL ON-CHAIN LIFECYCLE (GENLAYER STUDIO)");
    console.log("=====================================================================================");

    const deployData = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'deployment.json'), 'utf8'));
    const contractAddress = deployData.contractAddress;
    console.log("Target Contract Address:", contractAddress);
    console.log("Explorer URL:", deployData.explorerUrl);

    // Create Alice (investor) and Bob (recipient)
    const alice = createAccount();
    const bob = createAccount();
    console.log("Investor Alice Account:", alice.address);
    console.log("Recipient Bob Account :", bob.address);

    const clientAlice = createClient({
        endpoint: 'https://studio.genlayer.com/api',
        account: alice
    });

    const txRecords = [];

    // --- TX 1: REAL ON-CHAIN DEPOSIT & TOKEN MINT ---
    console.log("\n--- [TX 1] Real On-Chain Deposit: Alice deposits $500 USDC to mint ATK shares ---");
    try {
        const depositTx = await clientAlice.writeContract({
            address: contractAddress,
            functionName: 'deposit',
            args: [500],
            value: 0
        });
        console.log("Submitted deposit transaction! Tx Hash:", depositTx);
        console.log("Waiting for GenLayer validator consensus (FINALIZED)...");
        const receipt1 = await clientAlice.waitForTransactionReceipt({
            hash: depositTx,
            status: 'FINALIZED',
            interval: 3000,
            retries: 50
        });
        console.log("Receipt Status:", receipt1.status);
        console.log("Alice Deposit Finalized! Tx ID:", receipt1.tx_id || depositTx);
        txRecords.push({ action: "DEPOSIT", hash: depositTx, tx_id: receipt1.tx_id, amount: "$500 USDC" });

        // Query Alice's on-chain ATK token balance
        const aliceBal = await clientAlice.readContract({
            address: contractAddress,
            functionName: 'balanceOf',
            args: [alice.address]
        });
        console.log("On-Chain Verification -> Alice ATK Balance:", aliceBal.toString(), "shares");
    } catch (err) {
        console.error("Deposit Tx failed:", err);
    }

    // --- TX 2: REAL ON-CHAIN TOKEN TRANSFER ---
    console.log("\n--- [TX 2] Real On-Chain Transfer: Alice transfers 50 ATK tokens to Bob ---");
    try {
        const transferTx = await clientAlice.writeContract({
            address: contractAddress,
            functionName: 'transfer',
            args: [bob.address, 50],
            value: 0
        });
        console.log("Submitted transfer transaction! Tx Hash:", transferTx);
        console.log("Waiting for GenLayer validator consensus (FINALIZED)...");
        const receipt2 = await clientAlice.waitForTransactionReceipt({
            hash: transferTx,
            status: 'FINALIZED',
            interval: 3000,
            retries: 50
        });
        console.log("Receipt Status:", receipt2.status);
        console.log("Transfer Finalized! Tx ID:", receipt2.tx_id || transferTx);
        txRecords.push({ action: "TRANSFER", hash: transferTx, tx_id: receipt2.tx_id, amount: "50 ATK -> Bob" });

        const bobBal = await clientAlice.readContract({
            address: contractAddress,
            functionName: 'balanceOf',
            args: [bob.address]
        });
        console.log("On-Chain Verification -> Bob ATK Balance:", bobBal.toString(), "shares");
    } catch (err) {
        console.error("Transfer Tx failed:", err);
    }

    // --- TX 3: REAL ON-CHAIN REBALANCE MANDATE ---
    console.log("\n--- [TX 3] Real On-Chain AI Rebalance: Target Circle Arc Mainnet ---");
    try {
        const rebalanceTx = await clientAlice.writeContract({
            address: contractAddress,
            functionName: 'evaluate_and_rebalance',
            args: ['ARC_MAINNET'],
            value: 0
        });
        console.log("Submitted rebalance transaction! Tx Hash:", rebalanceTx);
        console.log("Waiting for GenLayer validator consensus (FINALIZED)...");
        const receipt3 = await clientAlice.waitForTransactionReceipt({
            hash: rebalanceTx,
            status: 'FINALIZED',
            interval: 4000,
            retries: 60
        });
        console.log("Receipt Status:", receipt3.status);
        console.log("Rebalance Finalized! Tx ID:", receipt3.tx_id || rebalanceTx);
        txRecords.push({ action: "REBALANCE", hash: rebalanceTx, tx_id: receipt3.tx_id, target: "ARC_MAINNET" });
    } catch (err) {
        console.error("Rebalance Tx failed:", err);
    }

    // --- TX 4: REAL ON-CHAIN WITHDRAWAL / REDEMPTION ---
    console.log("\n--- [TX 4] Real On-Chain Redemption: Alice burns 50 ATK shares for USDC payout ---");
    try {
        const withdrawTx = await clientAlice.writeContract({
            address: contractAddress,
            functionName: 'withdraw',
            args: [50],
            value: 0
        });
        console.log("Submitted withdraw transaction! Tx Hash:", withdrawTx);
        console.log("Waiting for GenLayer validator consensus (FINALIZED)...");
        const receipt4 = await clientAlice.waitForTransactionReceipt({
            hash: withdrawTx,
            status: 'FINALIZED',
            interval: 3000,
            retries: 50
        });
        console.log("Receipt Status:", receipt4.status);
        console.log("Withdraw Finalized! Tx ID:", receipt4.tx_id || withdrawTx);
        txRecords.push({ action: "WITHDRAW", hash: withdrawTx, tx_id: receipt4.tx_id, amount: "50 ATK burned" });
    } catch (err) {
        console.error("Withdraw Tx failed:", err);
    }

    // --- READ UPDATED ON-CHAIN TELEMETRY ---
    console.log("\n=====================================================================================");
    console.log("   FINAL ON-CHAIN TELEMETRY & TRANSACTION AUDIT TRAIL");
    console.log("=====================================================================================");
    const finalTelemetry = await clientAlice.readContract({
        address: contractAddress,
        functionName: 'get_fund_telemetry',
        args: []
    });
    console.log("Fund Telemetry:", JSON.stringify(finalTelemetry, null, 2));

    // Save transaction records
    const onchainHistoryPath = path.join(__dirname, '..', 'onchain_transactions.json');
    fs.writeFileSync(onchainHistoryPath, JSON.stringify({
        contractAddress: contractAddress,
        explorerUrl: deployData.explorerUrl,
        transactions: txRecords,
        finalTelemetry: finalTelemetry,
        executedAt: new Date().toISOString()
    }, null, 2), 'utf8');
    console.log(`\nSaved on-chain transaction history to ${onchainHistoryPath}`);
}

main();
