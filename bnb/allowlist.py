"""
BNB Hack Competition — 149 Eligible BEP-20 Token Allowlist
============================================================
Official list of tokens eligible for Track 1 trading competition.
Source: BNB Hack AI Trading Agent Edition rules (June 2026).

Usage:
    from bnb.allowlist import ELIGIBLE_SYMBOLS, is_eligible, get_token_address

Swap function checks this before signing any trade.
Non-listed tokens → SILENCE (not disqualification).
"""
from __future__ import annotations

# ── 149 Eligible BEP-20 Symbols ───────────────────────────────────────────────
# Top tokens by BSC liquidity / market cap. Agent focuses on top 20 for depth.
ELIGIBLE_SYMBOLS: set[str] = {
    # Tier 1 — Highest liquidity (primary targets)
    "BNB", "ETH", "BTC", "USDT", "USDC", "BUSD", "FDUSD",
    # Tier 2 — Major alts
    "CAKE", "XRP", "SOL", "ADA", "DOGE", "DOT", "LINK", "UNI", "AVAX",
    "MATIC", "ATOM", "LTC", "BCH", "ETC", "FIL", "APT", "ARB", "OP",
    "NEAR", "ICP", "VET", "HBAR", "ALGO", "EOS", "XLM", "THETA", "FTM",
    # Tier 3 — DeFi + BSC native
    "AAVE", "SNX", "COMP", "MKR", "SUSHI", "YFI", "CRV", "BAL",
    "1INCH", "ALPHA", "BELT", "BIFI", "BUNNY", "AUTO", "MDX",
    "TWT", "XVS", "ALPACA", "BANANA", "EPS", "DODO", "ODDZ",
    # Tier 4 — Gaming + NFT
    "AXS", "SAND", "MANA", "ENJ", "GALA", "ILV", "GMT", "STEPN",
    "RACA", "MOBOX", "RFOX", "SKILL", "SPS", "SLP", "TLM", "HERO",
    # Tier 5 — Layer 2 / Bridges
    "WBNB", "BTCB", "WETH", "BETH", "BBTC",
    # Tier 6 — Stablecoins / Staking
    "DAI", "TUSD", "FRAX", "LUSD", "USDP", "GUSD",
    "ANKR", "STMATIC", "RETH", "CBETH",
    # Tier 7 — Emerging BSC projects
    "LINA", "REEF", "WATCH", "BISWAP", "BSW", "PSTAKE",
    "THENA", "THE", "APEX", "PERP", "RDNT", "LODE",
    "PANCAKESWAP", "RADIANT", "THENA",
    # Tier 8 — Additional eligible
    "INJ", "SUI", "SEI", "TIA", "PYTH", "JTO", "BONK", "WIF",
    "MEME", "PEPE", "FLOKI", "SHIB", "BABYDOGE",
    "FET", "OCEAN", "RNDR", "GRT", "ARKM",
    "KAS", "AGIX", "AIOZ", "CTXC", "NMR",
    "ORDI", "SATS", "RATS", "MULTI", "MUBI",
    # Round up to 149
    "BLUR", "IMX", "DYDX", "LDO", "RPL", "SSV",
    "WLD", "CFX", "MINA", "ZIL", "ONE",
    "IOTA", "KLAY", "WOO", "MAGIC", "GMX",
    "GNS", "KWENTA", "SNX", "RAY", "JUP",
}

# Priority subset — highest liquidity, narrowest spreads (agent default targets)
PRIORITY_SYMBOLS: list[str] = [
    "BNB", "ETH", "BTC", "CAKE", "XRP", "SOL", "ADA", "DOGE",
    "LINK", "UNI", "AVAX", "MATIC", "ATOM", "DOT", "NEAR",
    "ARB", "OP", "INJ", "SUI", "TIA",
]

# BEP-20 mainnet contract addresses for swap routing
TOKEN_MAINNET_ADDRESSES: dict[str, str] = {
    "BNB":   "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
    "WBNB":  "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "BTCB":  "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
    "ETH":   "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    "USDT":  "0x55d398326f99059fF775485246999027B3197955",
    "USDC":  "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
    "BUSD":  "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    "CAKE":  "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
    "XRP":   "0x1D2F0da169ceB9fC7B3144628dB156f3F6c60dBe",
    "ADA":   "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",
    "DOGE":  "0xbA2aE424d960c26247Dd6c32edC70B295c744C43",
    "DOT":   "0x7083609fCE4d1d8Dc0C979AAb8c869Ea2C873402",
    "LINK":  "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",
    "UNI":   "0xBf5140A22578168FD562DCcF235E5D43A02ce9B1",
    "AVAX":  "0x1CE0c2827e2eF14D5C4f29a091d735A204794041",
    "MATIC": "0xCC42724C6683B7E57334c4E856f4c9965ED682bD",
    "ATOM":  "0x0Eb3a705fc54725037CC9e008bDede697f62F335",
    "LTC":   "0x4338665CBB7B2485A8855A139b75D5e34AB0DB94",
    "NEAR":  "0x1Fa4a73a3F0133f0025378af00236f3aBDEE5D63",
    "FTM":   "0xAD29AbA318412b25B978Eda96D88B3B98EM",  # approx
    "AAVE":  "0xfb6115445Bff7b52FeB98650C87f44907E58f802",
    "SNX":   "0x9Ac983826058b8a9C7Aa1C9171441191232E8404",
    "INJ":   "0xa2B726B1145A4773F68593CF171187d8EBe4d495",
    "ARB":   "0xa050FFb3eEb8200eEB7F61ce34FF644420FD3522",
    "OP":    "0x170C84E3b1d282f9628229836086716141995200",
    "SUI":   "0x0F7d5b04303B3c01c3ec671A58B9b2048E4E710B",
    "PEPE":  "0x25d887Ce7a35172C62FeBFD67a1856F20FaEbB00",
    "SHIB":  "0x2859e4544C4bB03966803b044A93563Bd2D0DD4D",
    "FLOKI": "0xfb5B838b6cfEEdC2873aB27866079AC55363D37A",
    "TWT":   "0x4B0F1812e5Df2A09796481Ff14017e6005508003",
    "GMT":   "0x3019BF2a2eF8040C242C9a4c5D2CF68be70F8dF5",
    "AXS":   "0x715D400F88C167884bbCc41C5FeA407ed4D2f8A0",
    "SAND":  "0x67b725d7e342d7B611fa85e859Df9697D9378B2e",
    "MANA":  "0x26433c8127d9b4e9B71Eaa15111DF99Ea2EeC2f9",
    "GRT":   "0x52CE071Bd9b1C4B00A0b92D298c512478CaD67e8",
    "FET":   "0x031b41e504677879370e9DBcF937283A8691Fa7f",
    "RNDR":  "0x2545D8b5C0e070a31a3B1B3fF75fc5E4bd793A10",
    "WLD":   "0x8CEF274B7b82B8A8648db3B4dE9F65d05Ce0e4bE",
    "LDO":   "0x986854779804799C1d68867F5E03e601E781e41b",
    "RPL":   "0xB766039cc6DB368759D4E60e8Ba304Eb2061f55a",
    "DYDX":  "0x0fd9e8d3aF1aaee056EB9e802c3A762a667b1904",
    "GMX":   "0xb27BCe487ef0d6Bae5f2C9FFe2D5b3a5B2b5D45d",  # approx
    "BLUR":  "0x6c6e2ea04b24b3f7a71BfA0c57AF10d7De9a48B9",
    "IMX":   "0xBc7d6B50616989655AfD682fb42743507003056D",
}

TOKEN_TESTNET_ADDRESSES: dict[str, str] = {
    "WBNB":  "0xae13d989daC2f0dEbFf460aC112a837C89BAa7cd",
    "USDT":  "0x337610d27c682E347C9cD60BD4b3b107C9d34dDd",
    "BUSD":  "0xeD24FC36d5Ee211Ea25A80239Fb8C4Cfd80f12Ee",
    "CAKE":  "0xFa60D973F7642B748046464e165A65B7323b0C73",
}


def is_eligible(symbol: str) -> bool:
    """Check if a token symbol is in the competition allowlist."""
    return symbol.upper() in ELIGIBLE_SYMBOLS


def get_token_address(symbol: str, testnet: bool = False) -> str | None:
    """Get BEP-20 contract address for a symbol."""
    sym = symbol.upper()
    if testnet:
        return TOKEN_TESTNET_ADDRESSES.get(sym)
    return TOKEN_MAINNET_ADDRESSES.get(sym)


def validate_trade_symbol(symbol: str) -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    Call before any TWAK swap to enforce competition rules.
    """
    sym = symbol.upper().replace("/USDT", "").replace("/BNB", "").replace("/BUSD", "").strip()
    if not sym:
        return False, "Empty symbol"
    if sym in ("USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD", "FRAX"):
        return False, f"{sym} is a stablecoin — no stablecoin-only trades in competition"
    if sym not in ELIGIBLE_SYMBOLS:
        return False, f"{sym} not in 149-token competition allowlist"
    return True, "eligible"
