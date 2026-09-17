// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

	/**
  * @title AlphaTankVault
  * @dev Autonomous Multi-Chain AI Hedge Fund Settlement Vault
  * Compatible with Coinbase Base Mainnet (Chain ID 8453) and Base Sepolia.
  * 
  * Enforces verifiable execution mandates dispatched by the GenLayer 
  * Intelligent Contract (AlphaTankBrain).
  */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

contract AlphaTankVault is IERC20 {
    // --- ERC-20 Token Metadata ---
    string public constant name = "AlphaTank Capital Share";
    string public constant symbol = "ATK";
    uint8 public constant decimals = 6; // Matching USDC decimals (6)

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    // --- Underlying Asset (USDC) ---
    address public immutable usdcToken;
    address public brainRelay;
    address public owner;

    // --- Net Asset Value (NAV) Accounting (BPS: 10,000 = $1.0000) ---
    uint256 public navPerShareBps = 10000;
    uint256 public totalAumUsdc;
    uint256 public rebalanceCounter;

    // --- Active Portfolio Weights (BPS) ---
    uint256 public btcWeightBps = 3000; // 30%
    uint256 public ethWeightBps = 3000; // 30%
    uint256 public solWeightBps = 2500; // 25%
    uint256 public cashWeightBps = 1500; // 15% minimum cash reserve
    bool public circuitBreakerActive;

    // --- Mandate Replay Protection ---
    mapping(bytes32 => bool) public executedMandates;

    // --- Events ---
    event Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares);
    event Withdraw(address indexed caller, address indexed receiver, uint256 assets, uint256 shares);
    event MandateExecuted(
        bytes32 indexed mandateHash,
        uint256 btcBps,
        uint256 ethbps,
        uint256 solBps,
        uint256 cashBps,
        uint256 newNavBps,
        bool circuitBreaker
    );
    event BrainRelayUpdated(address indexed previousRelay, address indexed newRelay);

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    modifier onlyRelayOrOwner() {
        require(msg.sender == brainRelay || msg.sender == owner, "NOT_AUTHORIZED_RELAY");
        _;
    }

    constructor(address _usdcToken, address _initialRelay) {
        require(_usdcToken != address(0), "ZERO_USDC");
        owner = msg.sender;
        usdcToken = _usdcToken;
        brainRelay = _initialRelay != address(0) ? _initialRelay : msg.sender;
    }

    // --- ERC-20 Standard Implementation ---
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 value) external override returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function allowance(address holder, address spender) external view override returns (uint256) {
        return _allowances[holder][spender];
    }

    function approve(address spender, uint256 value) external override returns (bool) {
        _approve(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external override returns (bool) {
        uint256 currentAllowance = _allowances[from][msg.sender];
        require(currentAllowance >= value, "ERC20: insufficient allowance");
        _approve(from, msg.sender, currentAllowance - value);
        _transfer(from, to, value);
        return true;
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(from != address(0), "ERC20: transfer from zero");
        require(to != address(0), "ERC20: transfer to zero");
        require(_balances[from] >= value, "ERC20: balance too low");

        _balances[from] -= value;
        _balances[to] += value;
        emit Transfer(from, to, value);
    }

    function _approve(address holder, address spender, uint256 value) internal {
        require(holder != address(0), "ERC20: approve from zero");
        require(spender != address(0), "ERC20: approve to zero");
        _allowances[holder][spender] = value;
        emit Approval(holder, spender, value);
    }

    // --- Vault Deposit & Redemption (ERC-4626 Style NAV Mechanics) ---

    /**
     * @notice Deposit USDC to mint ATK fund shares at current NAV%
     * @param usdcAmount Amount of USDC to deposit (6 decimals).
     * @return sharesMinted Number of ATK shares minted.
     */
    function deposit(uint256 usdcAmount) external returns (uint256 sharesMinted) {
        require(usdcAmount > 0, "ZERO_DEPOSIT");

        // Transfer USDC from user to vault
        bool success = IERC20(usdcToken).transferFrom(msg.sender, address(this), usdcAmount);
        require(success, "USDC_TRANSFER_FAILED");

        // Shares minted = (usdcAmount * 10,000) / navPerShareBps
        sharesMinted = (usdcAmount * 10000) / navPerShareBps;
        require(sharesMinted > 0, "ZERO_SHARES_MINTED");

        _totalSupply += sharesMinted;
        _balances[msg.sender] += sharesMinted;
        totalAumUsdc += usdcAmount;

        emit Deposit(msg.sender, msg.sender, usdcAmount, sharesMinted);
        emit Transfer(address(0), msg.sender, sharesMinted);
    }

    /**
     * @notice Redeem ATK shares for proportional USDC at current NAV.
     * @param sharesToBurn Number of ATK shares to redeem.
     * @return usdcPayout Amount of USDC transferred to caller.
     */
    function withdraw(uint256 sharesToBurn) external returns (uint256 usdcPayout) {
        require(sharesToBurn > 0, "ZERO_WITHDRAW");
        require(_balances[msg.sender] >= sharesToBurn, "INSUFFICIENT_SHARES");

        // USDC payout = (sharesToBurn * navPerShareBps) / 10,000
        usdcPayout = (sharesToBurn * navPerShareBps) / 10000;
        require(usdcPayout > 0, "ZERO_PAYOUT");
        require(totalAumUsdc >= usdcPayout, "INSUFFCIENT_AUM");

        _balances[msg.sender] -= sharesToBurn;
        _totalSupply -= sharesToBurn;
        totalAumUsdc -= usdcPayout;

        emit Transfer(msg.sender, address(0), sharesToBurn);
        emit Withdraw(msg.sender, msg.sender, usdcPayout, sharesToBurn);

        bool success = IERC20(usdcToken).transfer(msg.sender, usdcPayout);
        require(success, "USDC_PAYOUT_FAILED");
    }

    // --- Native ETH Support for Low-Friction L2 Execution ---

    /**
     * @notice Deposit native ETH on Base Sepolia to mint ATK fund shares at current NAV.
     * Treats 1 ETH as equivalent to $2,500 USDC collateral (6 decimals).
     * @return sharesMinted Number of ATK shares minted.
     */
    function depositETH() external payable returns (uint256 sharesMinted) {
        require(msg.value > 0, "ZERO_ETH_DEPOSIT");
        uint256 usdcValue = (msg.value * 2500) / 1e12;
        if (usdcValue == 0) usdcValue = 1;

        sharesMinted = (usdcValue * 10000) / navPerShareBps;
        require(sharesMinted > 0, "ZERO_SHARES_MINTED");

        _totalSupply += sharesMinted;
        _balances[msg.sender] += sharesMinted;
        totalAumUsdc += usdcValue;

        emit Deposit(msg.sender, msg.sender, usdcValue, sharesMinted);
        emit Transfer(address(0), msg.sender, sharesMinted);
    }

    receive() external payable {
        if (msg.value > 0) {
            uint256 usdcValue = (msg.value * 2500) / 1e12;
            if (usdcValue == 0) usdcValue = 1;
            uint256 sharesMinted = (usdcValue * 10000) / navPerShareBps;
            if (sharesMinted > 0) {
                _totalSupply += sharesMinted;
                _balances[msg.sender] += sharesMinted;
                totalAumUsdc += usdcValue;
                emit Deposit(msg.sender, msg.sender, usdcValue, sharesMinted);
                emit Transfer(address(0), msg.sender, sharesMinted);
            }
        }
    }

    /**
     * @notice Redeem ATK shares for proportional native ETH on Base Sepolia.
     * @param sharesToBurn Number of ATK shares to redeem.
     * @return ethPayout Amount of native ETH transferred to caller.
     */
    function withdrawETH(uint256 sharesToBurn) external returns (uint256 ethPayout) {
        require(sharesToBurn > 0, "ZERO_WITHDRAW");
        require(_balances[msg.sender] >= sharesToBurn, "INSUFFICIENT_SHARES");

        uint256 usdcPayout = (sharesToBurn * navPerShareBps) / 10000;
        require(usdcPayout > 0, "ZERO_PAYOUT");

        ethPayout = (usdcPayout * 1e12) / 2500;
        if (ethPayout > address(this).balance) {
            ethPayout = address(this).balance;
        }

        _balances[msg.sender] -= sharesToBurn;
        _totalSupply -= sharesToBurn;
        if (totalAumUsdc >= usdcPayout) {
            totalAumUsdc -= usdcPayout;
        }

        emit Transfer(msg.sender, address(0), sharesToBurn);
        emit Withdraw(msg.sender, msg.sender, usdcPayout, sharesToBurn);

        if (ethPayout > 0) {
            (bool success, ) = msg.sender.call{value: ethPayout}("");
            require(success, "ETH_PAYOUT_FAILED");
        }
    }

    // --- Autonomous GenLayer Settlement Execution ---

    /**
     * @notice Executes verified AI rebalancing mandate finalized by GenLayer.
     * @param mandateHash Unique 32-byte cryptographic digest of the mandate.
     * @param btcBps Target BTC allocation in basis points (max 3,500 bps).
     * @param ethBps Target ETH allocation in basis points (max 3,500 bps).
     * @param solBps Target SOL allocation in basis points (max 3,500 bps).
     * @param cashBps Target USDC cash allocation in basis points (min 1,500 bps).
     * @param newNavBps Audited post-rebalance NAV per share in basis points.
     */
    function executeRebalanceMandate(
        bytes32 mandateHash,
        uint256 btcBps,
        uint256 ethBps,
        uint256 solBps,
        uint256 cashBps,
        uint256 newNavBps
    ) external onlyRelayOrOwner {
        require(!executedMandates[mandateHash], "MANDATE_ALREADY_EXECUTED");
        require(btcBps + ethBps + solBps + cashBps == 10000, "WEIGHTS_MUST_SUM_10000");
        require(newNavBps > 0, "INVALID_NAV");

        bool isCircuitBreaker = (cashBps == 10000 && btcBps == 0 && ethBps == 0 && solBps == 0);

        if (!isCircuitBreaker) {
            // Strict Invariant Safeguards: Code-is-Law
            require(btcBps <= 3500, "EXCEEDS_35PCT_BTC_CAP");
            require(ethBps <= 3500, "EXCEEDS_35PCT_ETH_CAP");
            require(solBps <= 3500, "EXCEEDS_35PCT_SOL_CAP");
            require(cashBps >= 1500, "BELOW_15PCT_CASH_BUFFER");
        }

        // Apply Mandate Updates
        executedMandates[mandateHash] = true;
        btcWeightBps = btcBps;
        ethWeightBps = ethBps;
        solWeightBps = solBps;
        cashWeightBps = cashBps;
        navPerShareBps = newNavBps;
        circuitBreakerActive = isCircuitBreaker;
        rebalanceCounter += 1;

        // Recalculate AUM
        if (_totalSupply > 0) {
            totalAumUsdc = (_totalSupply * newNavBps) / 10000;
        }

        emit MandateExecuted(
            mandateHash,
            btcBps,
            ethBps,
            solBps,
            cashBps,
            newNavBps,
            isCircuitBreaker
        );
    }

    // --- Admin Configuration ---
    function setBrainRelay(address _newRelay) external onlyOwner {
        require(_newRelay != address(0), "ZERO_ADDRESS");
        emit BrainRelayUpdated(brainRelay, _newRelay);
        brainRelay = _newRelay;
    }
}
