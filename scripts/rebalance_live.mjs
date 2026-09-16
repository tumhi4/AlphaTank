import { createClient, createAccount } from '../../AetherDungeon/frontend/node_modules/genlayer-js/dist/index.js';

async function main() {
    console.log("=====================================================================================");
    console.log("   ALPHATANK CAPITAL — EXECUTING REAL ON-CHAIN REBALANCE ON GENLAYER STUDIO");
    console.log("=====================================================================================");
    const account = createAccount();
    console.log("Caller Account:", account.address);
    
    const client = createClient({
        endpoint: 'https://studio.genlayer.com/api',
        account: account
    });
    
    const contractAddress = '0x0615108Ea74a7C8d4B1Cb9B0aC12559BC9a380A7';
    console.log("Target Contract Address:", contractAddress);
    console.log("Broadcasting evaluate_and_rebalance('ARC_MAINNET') transaction...");
    
    try {
        const txHash = await client.writeContract({
            address: contractAddress,
            functionName: 'evaluate_and_rebalance',
            args: ['ARC_MAINNET'],
            value: 0
        });
        console.log("\nRebalance Transaction Submitted! Tx Hash:", txHash);
        console.log("Waiting for GenLayer Validators to execute Web consensus (FINALIZED)...");
        
        const receipt = await client.waitForTransactionReceipt({
            hash: txHash,
            status: 'FINALIZED',
            interval: 4000,
            retries: 60
        });
        
        console.log("Receipt status:", receipt.status);
        console.log("Execution Result:", receipt.txExecutionResultName || receipt.data?.txExecutionResultName);
        console.log("Transaction ID:", receipt.tx_id || txHash);
        console.log("Number of validator rounds:", receipt.data?.num_of_rounds || receipt.num_of_rounds);
        
        console.log("\nReading updated contract state after on-chain rebalance...");
        const telemetry = await client.readContract({
            address: contractAddress,
            functionName: 'get_fund_telemetry',
            args: []
        });
        console.log("Updated Live Fund Telemetry:\n", JSON.stringify(telemetry, null, 2));
    } catch (e) {
        console.error("Rebalance execution failed:", e);
    }
}

main();
