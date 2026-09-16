import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createClient, createAccount } from '../../AetherDungeon/frontend/node_modules/genlayer-js/dist/index.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function main() {
    console.log("=====================================================================================");
    console.log("   ALPHATANK CAPITAL -- DEPLOYING INTELLIGENT CONTRACT TO GENLAYER ");
    console.log("=====================================================================================");
    console.log("Initializing GenLayer Studio RPC: https://studio.genlayer.com/api");
    const account = createAccount();
    console.log("Generated Deployer Account:", account.address);
    
    const client = createClient({
        endpoint: 'https://studio.genlayer.com/api',
        account: account
    });
    
    const contractPath = path.join(__dirname, '..', 'contracts', 'AlphaTankBrain.py');
    const code = fs.readFileSync(contractPath, 'utf8');
    console.log(`Read contract code: ${code.length} bytes`);
    
    const operator = account.address;
    console.log("Setting fund operator to:", operator);
    
    console.log("\nBroadcasting deployContract transaction to GenLayer Studio...");
    try {
        const txHash = await client.deployContract({
            code: code,
            args: [operator]
        });
        console.log("Deployment transaction submitted! Tx Hash:", txHash);
        
        console.log("Waiting for transaction receipt on GenLayer (Status: FINALIZED)...");
        const receipt = await client.waitForTransactionReceipt({
            hash: txHash,
            status: 'FINALIZED',
            interval: 3000,
            retries: 40
        });
        console.log("Receipt status:", receipt.status);
        const contractAddress = receipt.contractAddress || receipt.data?.contractAddress || receipt.recipient;
        console.log("Contract Address:", contractAddress);
        
        if (contractAddress) {
            console.log("\n====================================================================================");
            console.log(">>> DEPLOYMENT SUCCESSFUL! <<<");
            console.log("Contract Address:", contractAddress);
            console.log("Explorer URL: https://explorer-studio.genlayer.com/address/" + contractAddress);
            console.log("=====================================================================================\n");
            
            console.log("Verifying live on-chain state via readContract(get_fund_telemetry)...");
            try {
                const telemetry = await client.readContract({
                    address: contractAddress,
                    functionName: 'get_fund_telemetry',
                    args: []
                });
                console.log("Live Fund Telemetry:", JSON.stringify(telemetry, null, 2));
            } catch (vErr) {
                console.log("Telemetry check note:", vErr.message);
            }

            const deployRecord = {
                network: "GenLayer Studio Testnet",
                rpc: "https://studio.genlayer.com/api",
                contractAddress: contractAddress,
                deployer: operator,
                txHash: txHash,
                deployedAt: new Date().toISOString(),
                explorerUrl: `https://explorer-studio.genlayer.com/address/${contractAddress}`
            };
            const deployPath = path.join(__dirname, '..', 'deployment.json');
            fs.writeFileSync(deployPath, JSON.stringify(deployRecord, null, 2), 'utf8');
            console.log(`Saved deployment details to ${deployPath}`);
        }
    } catch (err) {
        console.error("Deployment failed:", err);
        process.exit(1);
    }
}

main();