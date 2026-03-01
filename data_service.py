import requests
import logging
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchResults
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import mplfinance as mpf
import os

@tool
def get_crypto_data(coin_ids_csv: str) -> str:
    """
    Busca os preços reais, variação de 24h e volume de 24h de criptomoedas no CoinGecko.
    Args:
        coin_ids_csv: APENAS o símbolo/ticker da moeda (ex: "btc", "hype", "pol", "eth") ou o nome exato (ex: "bitcoin"). 
                      NÃO envie frases como "token hype" ou "moeda pol". Envie APENAS a sigla ou nome, separados por vírgula.
    """
    if not coin_ids_csv or coin_ids_csv.strip() == "":
        return "Erro: Nenhum ID de moeda foi fornecido."
        
    # Mapeamentos comuns para ajudar o robo a encontrar o ID correto na CoinGecko
    COIN_ID_MAP = {
        "hype": "hyperliquid",
        "pol": "polygon-ecosystem-token",
        "matic": "polygon-ecosystem-token",
        "btc": "bitcoin",
        "eth": "ethereum",
        "sol": "solana",
        "bnb": "binancecoin",
        "arb": "arbitrum",
        "op": "optimism",
        "ton": "the-open-network",
        "avax": "avalanche-2",
        "ada": "cardano",
        "dot": "polkadot",
        "link": "chainlink",
        "doge": "dogecoin",
        "shib": "shiba-inu",
        "pepe": "pepe",
        "wif": "dogwifcoin",
        "rndr": "render-token",
        "fet": "fetch-ai",
        "agix": "singularitynet",
        "inj": "injective-protocol",
        "tao": "bittensor",
        "kas": "kaspa",
        "mkr": "maker",
        "aave": "aave",
        "uni": "uniswap",
        "ldo": "lido-dao",
        "xrp": "ripple",
        "snx": "havven",
        "imx": "immutable-x"
    }
    
    # Limpa e mapeia os ids providos pelo LLM
    # Removemos palavras sujas que o LLM as vezes manda ("token", "moeda", "da", "rede")
    raw_ids = []
    for c in coin_ids_csv.split(','):
        clean_c = c.lower().strip()
        for dirty_word in ["token ", "moeda ", "coin ", "da ", "rede ", "crypto "]:
            clean_c = clean_c.replace(dirty_word, "")
        clean_c = clean_c.strip()
        if clean_c:
            raw_ids.append(clean_c)
            
    mapped_ids = [COIN_ID_MAP.get(cid, cid) for cid in raw_ids if cid]
    final_ids_csv = ",".join(mapped_ids)
    
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={final_ids_csv}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return f"Não foram encontrados dados ativos para as moedas: {final_ids_csv} (Original: {coin_ids_csv})"
            
        contexto_precos = "Dados REAIS atuais do CoinGecko:\n"
        for coin_id, info in data.items():
            preco = info.get('usd', 0)
            variacao = info.get('usd_24h_change', 0)
            vol = info.get('usd_24h_vol', 0)
            
            if vol >= 1_000_000_000:
                vol_str = f"${vol / 1_000_000_000:.2f}B"
            elif vol >= 1_000_000:
                vol_str = f"${vol / 1_000_000:.2f}M"
            else:
                vol_str = f"${vol:,.0f}"

            # Mapeamento reverso para enviar o nome real/bonito para a IA ao invés do ID interno feio da CoinGecko
            REVERSE_NAME_MAP = {
                "havven": "Synthetix (SNX)",
                "polygon-ecosystem-token": "Polygon (POL)",
                "hyperliquid": "Hyperliquid (HYPE)",
                "avalanche-2": "Avalanche (AVAX)",
                "the-open-network": "Toncoin (TON)",
                "dogwifcoin": "Dogwifhat (WIF)",
                "shiba-inu": "Shiba Inu (SHIB)",
                "injective-protocol": "Injective (INJ)",
                "render-token": "Render (RNDR)",
                "fetch-ai": "Fetch.ai (FET)",
                "singularitynet": "SingularityNET (AGIX)"
            }
            display_name = REVERSE_NAME_MAP.get(coin_id, coin_id.capitalize())
                
            contexto_precos += f"- {display_name}: Preço ${preco:,.2f} | Variação 24h: {variacao:+.2f}% | Volume 24h: {vol_str}\n"
            
        return contexto_precos
    except Exception as e:
        logging.warning(f"Erro ao buscar dados do CoinGecko na Tool: {e}. Tentando fallback CryptoCompare...")
        try:
            # Fallback CryptoCompare
            cc_ids = [c.upper() for c in raw_ids if c]
            if not cc_ids:
                return "Erro: Nenhum ID válido para busca."
                
            cc_ids_csv = ",".join(cc_ids)
            url_cc = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={cc_ids_csv}&tsyms=USD"
            resp_cc = requests.get(url_cc, timeout=5)
            resp_cc.raise_for_status()
            data_cc = resp_cc.json()
            
            raw_data = data_cc.get('RAW', {})
            if not raw_data:
                return f"Não foram encontrados dados ativos (Fallback) para as moedas: {final_ids_csv}"
                
            contexto_precos = "Dados REAIS atuais (via CryptoCompare):\n"
            for coin_id, info in raw_data.items():
                usd_info = info.get('USD', {})
                preco = usd_info.get('PRICE', 0)
                variacao = usd_info.get('CHANGEPCT24HOUR', 0)
                vol = usd_info.get('VOLUME24HOURTO', 0)
                
                if vol >= 1_000_000_000:
                    vol_str = f"${vol / 1_000_000_000:.2f}B"
                elif vol >= 1_000_000:
                    vol_str = f"${vol / 1_000_000:.2f}M"
                else:
                    vol_str = f"${vol:,.0f}"

                # Mapeamento reverso para exibir nome amigável
                REVERSE_NAME_MAP = {
                    "SNX": "Synthetix (SNX)", "POL": "Polygon (POL)", "HYPE": "Hyperliquid (HYPE)",
                    "AVAX": "Avalanche (AVAX)", "TON": "Toncoin (TON)", "WIF": "Dogwifhat (WIF)",
                    "SHIB": "Shiba Inu (SHIB)", "INJ": "Injective (INJ)", "RNDR": "Render (RNDR)",
                    "FET": "Fetch.ai (FET)", "AGIX": "SingularityNET (AGIX)"
                }
                display_name = REVERSE_NAME_MAP.get(coin_id, coin_id)
                    
                contexto_precos += f"- {display_name}: Preço ${preco:,.2f} | Variação 24h: {variacao:+.2f}% | Volume 24h: {vol_str}\n"
                
            return contexto_precos
        except Exception as fallback_error:
            logging.error(f"Erro no fallback CryptoCompare: {fallback_error}")
            return "Ocorreu um erro nas fontes de dados (CoinGecko e Fallback). Informe ao usuário que os dados ao vivo estão indisponíveis no momento."

@tool
def get_defi_pools(chain_names_csv: str) -> str:
    """
    Busca as melhores pools de liquidez (rendimento/APY) ativas no DefiLlama para uma ou mais redes.
    Args:
        chain_names_csv: Nome da rede (ex: 'Ethereum') ou uma lista (ex: 'Ethereum,Base,Hyperliquid,Arbitrum').
    """
    url = "https://yields.llama.fi/pools"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        pools = data.get('data', [])
        
        chains = [c.strip().lower() for c in chain_names_csv.split(',')]
        
        # Protocolos autorizados (Concentrated Liquidity e principais DEXs solicitadas)
        ALLOWED_DEXS = ['aerodrome', 'projectx', 'uniswap', 'meteora', 'raydium', 'orca']
        
        # Filtra pelas pools das redes solicitadas com TVL maior que $1M e apenas nos protocolos permitidos
        pools_filtradas = []
        for p in pools:
            chain_match = p.get('chain', '').lower().strip() in chains
            tvl_match = p.get('tvlUsd', 0) > 1_000_000
            project_name = p.get('project', '').lower().strip().replace(' ', '') # remove spaces for projectx match
            protocol_match = any(dex in project_name for dex in ALLOWED_DEXS)
            
            if chain_match and tvl_match and protocol_match:
                pools_filtradas.append(p)
                
        pools_ordenadas = sorted(pools_filtradas, key=lambda x: x.get('apy', 0), reverse=True)
        
        if not pools_ordenadas:
            return f"Nenhuma pool relevante (TVL > 1M) foi encontrada no momento para as redes: {chain_names_csv}"
            
        contexto_pools = f"Melhores pools de liquidez nas redes {chain_names_csv} (Fonte: DefiLlama):\n"
        
        # Pega as 5 melhores no geral, ou o LLM pode filtrar. Vamos enviar o top 6.
        for i, pool in enumerate(pools_ordenadas[:6]):
            tvl = pool.get('tvlUsd', 0)
            if tvl >= 1_000_000_000:
                tvl_str = f"${tvl / 1_000_000_000:.2f}B"
            else:
                tvl_str = f"${tvl / 1_000_000:.2f}M"
                
            projeto = pool.get('project', 'Desconhecido').capitalize()
            symbol = pool.get('symbol', 'Desconhecido')
            apy = pool.get('apy', 0)
            chain_pool = pool.get('chain', 'Unknown')
            contexto_pools += f"- {i+1}º na rede {chain_pool}: {projeto} ({symbol}) | TVL: {tvl_str} | APY: {apy:.2f}%\n"
            
        return contexto_pools
    except Exception as e:
        logging.error(f"Erro ao buscar dados do DefiLlama na Tool: {e}")
        return "Ocorreu um erro ao buscar pools de DeFi no momento."

@tool
def search_web_news(query: str) -> str:
    """
    Realiza uma pesquisa na internet (WEB SEARCH) para obter notícias atualizadas sobre macroeconomia, geopolítica ou eventos de mercado em tempo real.
    Args:
        query: O termo de busca para pesquisar no Google/DuckDuckGo.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        data = {"q": query}
        response = requests.post(url, data=data, headers=headers, timeout=5)
        
        if response.status_code == 200:
            html = response.text
            # Extração tosca pra pegar as descricoes dos resultados no DDG Lite HTML
            snippets = []
            partes = html.split('a class="result__snippet')
            for p in partes[1:4]:
                if 'href=' in p:
                    ext = p.split('>', 1)[1].split('</a>', 1)[0]
                    snippets.append(ext.replace('<b>', '').replace('</b>', ''))
            return "Últimas Notícias: " + " | ".join(snippets)
        return "Notícias não puderam ser carregadas por lentidão na API."
    except Exception as e:
        logging.error(f"Erro ao buscar na Web na Tool: {e}")
        return f"Não foi possível acessar a internet para pesquisar sobre {query} no momento."

@tool
def get_market_metrics(query_type: str, pair: str = None) -> str:
    """
    Busca métricas avançadas de mercado estilo TradingView.
    Args:
        query_type: 'dominance' (para buscar a dominância do BTC, ETH e OTHERS) ou 'pair' (para cruzamentos de moeda).
        pair: Obrigatório apenas se query_type for 'pair'. O par exato na Binance. (Exemplo: "ETHBTC", "SOLBTC", "BNBBTC"). NÃO incluir barras.
    """
    try:
        if query_type == "dominance":
            # API global do CoinGecko para Market Cap Percentage
            url = "https://api.coingecko.com/api/v3/global"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json().get('data', {})
            
            market_cap_pct = data.get('market_cap_percentage', {})
            btc_dom = market_cap_pct.get('btc', 0)
            eth_dom = market_cap_pct.get('eth', 0)
            
            # Cálculo de OTHERS (Todo o mercado menos top 10 listadas na dominância)
            # Para simplificar a visão popular do trading view: Others.D exclui o peso do BTC e ETH e Stablecoins principais, mas vamos pegar a soma geral
            outros_principais = sum([v for k, v in market_cap_pct.items() if k not in ['btc', 'eth', 'usdt', 'usdc']])
            
            return (f"Métricas Globais de Dominância (TradingView Like):\n"
                    f"- Dominância BTC (BTC.D): {btc_dom:.2f}%\n"
                    f"- Dominância ETH (ETH.D): {eth_dom:.2f}%\n"
                    f"- OTHERS (Altcoins Totais exceto Majors): Aproximadamente {outros_principais:.2f}% do Capital Total do Mercado\n")
            
        elif query_type == "pair" and pair:
            # API da Binance para buscar o par exato
            pair = pair.upper().strip().replace("/", "")
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                preco = data.get('price', '0')
                return f"Cotação em tempo real na Binance:\nO par {pair} está sendo negociado a {preco}"
            else:
                return f"Não foi possível encontrar o par cruzado {pair} na Binance. Verifique se o símbolo está correto (ex: ETHBTC)."
                
        else:
            return "Erro: query_type inválido ou argumento 'pair' faltando."
    except Exception as e:
        logging.error(f"Erro em Market Metrics Tool: {e}")
        return "As métricas de mercado (Dominância ou Pares) estão indisponíveis no servidor original no momento."

@tool
def get_coinglass_metrics(symbol: str) -> str:
    """
    Busca dados avançados de derivativos (Open Interest, Funding Rate) essenciais para mapa de liquidação.
    Args:
        symbol: Ticker do par futuro. Exemplo: "BTC", "ETH", "SOL". (O bot adicionará 'USDT' automaticamente).
    """
    try:
        # Usando a Binance Futures API pública gratuita (equivalente aos dados base da Coinglass para OI e Funding)
        symbol = symbol.upper().strip()
        pair_futures = f"{symbol}USDT"
        
        # Funding Rate
        fr_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={pair_futures}"
        fr_response = requests.get(fr_url, timeout=5)
        
        # Open Interest
        oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={pair_futures}"
        oi_response = requests.get(oi_url, timeout=5)
        
        if fr_response.status_code == 200 and oi_response.status_code == 200:
            fr_data = fr_response.json()
            oi_data = oi_response.json()
            
            # Funding rate vem em decimal. Ex: 0.0001 = 0.01% (a cada 8 horas)
            funding_rate_raw = float(fr_data.get('lastFundingRate', 0))
            funding_rate_pct = funding_rate_raw * 100
            
            # Formata sentimento de acordo com o FR
            if funding_rate_pct > 0.01:
                sentimento_fr = "🚨 Muito Alto (Longs pagando Shorts, risco de squeeze de alta alavancagem)"
            elif funding_rate_pct > 0:
                sentimento_fr = "📈 Positivo (Maioria apostando na alta)"
            elif funding_rate_pct < -0.01:
                sentimento_fr = "⚠️ Muito Negativo (Shorts pagando Longs, risco de short squeeze violentos)"
            else:
                sentimento_fr = "📉 Negativo (Maioria apostando na baixa)"
                
            open_interest = float(oi_data.get('openInterest', 0))
            
            return (f"Métricas de Derivativos e Liquidez ({symbol} - Mercado Futuro):\n"
                    f"- Open Interest (Contratos em Aberto): {open_interest:,.2f} {symbol}\n"
                    f"- Funding Rate Atual (8h): {funding_rate_pct:.4f}%\n"
                    f"- Sentimento da Alavancagem: {sentimento_fr}\n"
                    f"Use esses dados para prever se há risco de violinada (liquidações em massa).")
        else:
            return f"Não foram encontrados dados de derivativos para {symbol}."
            
    except Exception as e:
        logging.error(f"Erro em Derivativos/Coinglass Tool: {e}")
        return f"Os dados de derivativos (OI, Funding) estão inacessíveis no momento."

@tool
def get_market_sentiment(dummy: str = "") -> str:
    """
    Busca o Fear & Greed Index global e o MVRV Z-Score do Bitcoin. Usar quando o usuário pedir análise técnica ou de sentimento.
    Args:
        dummy: Argumento não utilizado, ignore.
    """
    contexto = "Métricas Globais de Sentimento do Mercado:\n"
    
    # Fear & Greed
    try:
        url_fg = "https://api.alternative.me/fng/?limit=1"
        resp_fg = requests.get(url_fg, timeout=5)
        if resp_fg.status_code == 200:
            fg_data = resp_fg.json().get('data', [])[0]
            contexto += f"- Fear & Greed Index: {fg_data.get('value')} ({fg_data.get('value_classification')})\n"
    except Exception as e:
        logging.error(f"Erro Fear & Greed: {e}")
        
    # MVRV Z-Score
    try:
        url_mvrv = "https://bitcoin-data.com/v1/mvrv-zscore/1"
        resp_mvrv = requests.get(url_mvrv, timeout=5)
        if resp_mvrv.status_code == 200:
            mvrv_data = resp_mvrv.json()
            if isinstance(mvrv_data, list):
                mvrv_data = mvrv_data[0]
            mvrv_value = float(mvrv_data.get("mvrvZscore", 0))
            
            if mvrv_value > 7:
                mvrv_txt = "🚨 Tope de Mercado Histórico (Maior que 7)"
            elif mvrv_value > 3:
                mvrv_txt = "⚠️ Região de Risco Elevado (Maior que 3)"
            elif mvrv_value < 0:
                mvrv_txt = "🟢 Super Subvalorizado (Abaixo de 0)"
            elif mvrv_value < 1:
                mvrv_txt = "✅ Zona de Acumulação"
            else:
                mvrv_txt = "🟡 Faixa Neutra / Transição"
                
            contexto += f"- MVRV Z-Score (Bitcoin): {mvrv_value:.2f} -> {mvrv_txt}\n"
    except Exception as e:
        logging.error(f"Erro MVRV Z-Score: {e}")
        
        
    return contexto

@tool
def get_defi_protocol_metrics(protocol_name: str) -> str:
    """
    Busca métricas fundamentalistas de um protocolo DeFi específico (TVL total, TVL por rede) no DefiLlama. Usar quando pedirem análise de um protocolo específico.
    Args:
        protocol_name: O nome exato ou slug do protocolo (ex: "uniswap", "aave", "lido", "makerdao").
    """
    slug = protocol_name.lower().strip().replace(' ', '-')
    url = f"https://api.llama.fi/protocol/{slug}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            nome = data.get('name', protocol_name.capitalize())
            tvl_data = data.get('tvl', [])
            tvl_atual = tvl_data[-1].get('totalLiquidityUSD', 0) if tvl_data else 0
            
            # Formatar TVL
            if tvl_atual >= 1_000_000_000:
                tvl_str = f"${tvl_atual / 1_000_000_000:.2f}B"
            elif tvl_atual >= 1_000_000:
                tvl_str = f"${tvl_atual / 1_000_000:.2f}M"
            else:
                tvl_str = f"${tvl_atual:,.0f}"
                
            redes = data.get('currentChainTvls', {})
            # Filtrar e pegar as top 3 redes reais, removendo tokens staking/pool categories if any
            redes_reais = {k: v for k, v in redes.items() if not '-' in k and isinstance(v, (int, float))}
            top_redes = list(sorted(redes_reais.items(), key=lambda x: float(x[1]), reverse=True))[:3]
            
            redes_str = " | ".join([
                f"{k}: ${v/1_000_000:.1f}M" if v < 1_000_000_000 else f"{k}: ${v/1_000_000_000:.1f}B" 
                for k, v in top_redes
            ])
            
            return (f"Fundamentos DeFi - Protocolo {nome} (DefiLlama):\n"
                    f"- TVL Total: {tvl_str}\n"
                    f"- Principais Redes (TVL): {redes_str}")
        else:
            return f"Não foi possível encontrar dados para o protocolo '{protocol_name}' no banco do DefiLlama. Tente o nome exato / slug."
    except Exception as e:
        logging.error(f"Erro ao buscar fundamentos do protocolo na Tool: {e}")
        return f"As métricas do protocolo {protocol_name} estão indisponíveis no momento pelo DefiLlama."
@tool
def generate_crypto_chart(symbol: str) -> str:
    """
    Gera um gráfico visual de velas (Candlestick) de uma criptomoeda. Chame esta ferramenta se o usuário pedir para 'ver o gráfico', 'mostrar o gráfico' ou 'gerar imagem'.
    Args:
        symbol: O ticker/símbolo da moeda (Ex: "BTC", "ETH", "SOL", "PEPE").
    Returns:
        Um aviso pro robô informando o caminho do arquivo gerado para que ele anexe na mensagem.
    """
    try:
        symbol = symbol.upper().strip()
        pair = f"{symbol}USDT"
        
        # Tenta Binance primeiro (Tem dados de Volume)
        url_binance = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1d&limit=100"
        response = requests.get(url_binance, timeout=10)
        
        usou_coingecko = False
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 
                'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
        else:
            # Fallback para CoinGecko se Binance não tiver o par (Ex: HYPE, etc)
            COIN_ID_MAP = {
                "HYPE": "hyperliquid", "POL": "polygon-ecosystem-token", "MATIC": "polygon-ecosystem-token",
                "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
                "ARB": "arbitrum", "OP": "optimism", "TON": "the-open-network", "AVAX": "avalanche-2",
                "ADA": "cardano", "DOT": "polkadot", "LINK": "chainlink", "DOGE": "dogecoin",
                "SHIB": "shiba-inu", "PEPE": "pepe", "WIF": "dogwifcoin", "RNDR": "render-token",
                "FET": "fetch-ai", "AGIX": "singularitynet", "INJ": "injective-protocol",
                "TAO": "bittensor", "KAS": "kaspa", "MKR": "maker", "AAVE": "aave",
                "UNI": "uniswap", "LDO": "lido-dao", "XRP": "ripple", "SNX": "havven", "IMX": "immutable-x"
            }
            cg_id = COIN_ID_MAP.get(symbol, symbol.lower())
            
            # Pega as velas (diárias aproximadas)
            url_cg = f"https://api.coingecko.com/api/v3/coins/{cg_id}/ohlc?vs_currency=usd&days=30"
            resp_cg = requests.get(url_cg, timeout=10)
            
            if resp_cg.status_code != 200:
                return f"Não foi possível buscar os dados do gráfico para {symbol} na Binance nem na CoinGecko. Tente usar apenas o texto."
                
            data = resp_cg.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            df['volume'] = 0.0 # CG doesn't provide volume in OHLC endpoint
            usou_coingecko = True
            
        df.set_index('timestamp', inplace=True)
        
        # Estilo escuro (TradingView style)
        mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in', ohlc='i')
        s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds', gridstyle='dotted')
        
        filename = f"chart_{symbol}.png"
        chart_path = os.path.join(os.getcwd(), filename)
        
        # Se usou coingecko, não desenhar o painel de volume
        kwargs_plot = {
            'type': 'candle', 
            'style': s, 
            'title': f"\n{symbol}/USDT - Grafico Diario", 
            'ylabel': 'Preco (USD)', 
            'savefig': {'fname': chart_path, 'dpi': 120, 'bbox_inches': 'tight'}
        }
        
        if not usou_coingecko:
            kwargs_plot['volume'] = True
            kwargs_plot['ylabel_lower'] = 'Volume'
            
        mpf.plot(df, **kwargs_plot)
        
        return f"[CHART_GENERATED:{filename}] Gráfico de {symbol} gerado com sucesso em: {chart_path}. INSTRUÇÃO CRÍTICA: Avise ao usuário no texto que você está enviando o gráfico em anexo."

    except Exception as e:
        logging.error(f"Erro ao gerar gráfico para {symbol}: {e}")
        return f"Ocorreu um erro interno ao tentar desenhar o gráfico matemático de {symbol}."


@tool
def get_whale_vs_retail_sentiment(symbol: str) -> str:
    """
    Busca o ratio Long/Short dos Top Traders (Baleias/Smart Money) diretamente na Binance Futures.
    Args:
        symbol: Símbolo da criptomoeda (Ex: BTC, ETH, SOL).
    """
    try:
        symbol = symbol.upper().strip()
        pair = f"{symbol}USDT"
        url = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={pair}&period=1d&limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list):
                 ratio = float(data[0].get('longShortRatio', 0))
                 long_pct = float(data[0].get('longAccount', 0)) * 100
                 short_pct = float(data[0].get('shortAccount', 0)) * 100
                 
                 return (f"Posicionamento Baleias (Top Traders Binance) para {symbol}:\n"
                         f"- Ratio Long/Short: {ratio:.2f}\n"
                         f"- {long_pct:.1f}% em Longs / {short_pct:.1f}% em Shorts. Interprete isso!")
            return f"Sem dados avançados de Whale/Retail para {symbol}."
        return f"A API da Binance falhou na resposta para {symbol}."
    except Exception as e:
         logging.error(f"Erro Whale/Retail Tool: {e}")
         return f"Dados indisponíveis para Smart Money em {symbol}."

@tool
def get_protocol_revenue(protocol_name: str) -> str:
    """
    Busca a receita e taxas geradas diariamente (Fees/Revenue) de um protocolo específico no DefiLlama. Proxy gratuito para dados do Token Terminal/Fundamentos Econômicos.
    Args:
        protocol_name: Nome exato ou slug do protocolo (ex: "uniswap", "aave", "lido", "pump.fun").
    """
    try:
        url = "https://api.llama.fi/overview/fees?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyFees"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            protocols = data.get('protocols', [])
            
            prot = None
            term = protocol_name.lower().strip()
            for p in protocols:
                if term in p.get('name', '').lower() or term in p.get('module', '').lower():
                    prot = p
                    break
                    
            if prot:
                nome = prot.get('name', protocol_name)
                fees_24h = prot.get('total24h')
                if not fees_24h:
                    fees_24h = 0
                
                if fees_24h >= 1_000_000:
                    fees_str = f"${fees_24h / 1_000_000:.2f}M"
                else:
                    fees_str = f"${fees_24h:,.0f}"
                    
                return f"Fundamentos Financeiros de {nome} (Fonte: DefiLlama | Alternativa Token Terminal):\n- Taxas geradas (Fees) em 24h: {fees_str}"
        return f"Não foi possível encontrar a receita diária para o protocolo {protocol_name} no histórico."
    except Exception as e:
        logging.error(f"Erro Defi Fees Tool: {e}")
        return f"Não foi possível buscar as receitas para o protocolo {protocol_name} no momento."

@tool
def search_institutional_news(query: str) -> str:
    """
    Busca relatórios e notícias profundas voltadas para o lado Institucional do mercado (buscando especificamente em The Block e Santiment).
    Args:
        query: O termo de busca que o agente quer extrair opiniões institucionais (ex: "Bitcoin ETFs", "Ethereum network growth").
    """
    try:
        busca_fechada = f"{query} site:theblock.co OR site:santiment.net"
        pesquisa = DuckDuckGoSearchResults()
        resultados = pesquisa.run(busca_fechada)
        
        if resultados:
            return f"Visão Institucional (The Block / Santiment): {resultados}"
        return "Notícias institucionais indisponíveis por lentidão na interface."
    except Exception as e:
        logging.error(f"Erro Institutional News Tool: {e}")
        return f"Falha na busca institucional para {query}."
