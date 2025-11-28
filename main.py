import json
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import re # Importado para usar regex na extração da temporada

# --- CONFIGURAÇÕES GLOBAIS ---
# Usamos o Service() vazio para que o Selenium Manager (nativo) cuide do driver
SERVICE = Service() 
OPTIONS = webdriver.ChromeOptions()
# Verifica se estamos no Linux Mint para definir o caminho do Chromium
# (Pode ser necessário ajustar se o caminho for diferente em outras distros)
try:
    with open('/etc/os-release') as f:
        if 'ID=linuxmint' in f.read():
             OPTIONS.binary_location = "/usr/bin/chromium" # AJUSTADO - Caminho para Chromium no Mint
except FileNotFoundError:
     # Se não for Mint ou o arquivo não existir, Selenium tentará encontrar o Chrome/Chromium padrão
     print("Não foi possível detectar o Mint ou encontrar /etc/os-release. Usando navegador padrão.")
     pass

def setup_driver():
    """Inicializa e retorna o WebDriver."""
    # Tratamento de erro caso o binário não seja encontrado no caminho especificado
    try:
        driver = webdriver.Chrome(service=SERVICE, options=OPTIONS)
        return driver
    except Exception as e:
        print(f"Erro ao inicializar o WebDriver: {e}")
        print("Verifique se o Chrome/Chromium está instalado e se o caminho em OPTIONS.binary_location está correto.")
        # Tenta sem o binary_location como fallback
        print("Tentando inicializar sem especificar o caminho do binário...")
        try:
            options_fallback = webdriver.ChromeOptions()
            driver = webdriver.Chrome(service=Service(), options=options_fallback)
            print("WebDriver inicializado com sucesso (sem caminho específico).")
            return driver
        except Exception as fallback_e:
            print(f"Falha ao inicializar o WebDriver (fallback): {fallback_e}")
            print("Certifique-se de que o WebDriver correto está no PATH ou use webdriver-manager.")
            exit() # Sai do script se não conseguir iniciar o driver


def scraper_nba_stats(driver):
    """
    Método 1: Scraper NBA Stats
    Endpoint: https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season
    """
    URL = "https://www.nba.com/stats/players/traditional?Season=2025-26&SeasonType=Regular%20Season"
    JSON_FILENAME = "nba_stats_2025_26_players_filtrado.json"
    all_records_df = pd.DataFrame()

    print("=" * 50)
    print("INICIANDO SCRAPER 1: NBA PLAYER STATS")
    print(f"Acessando o endpoint: {URL}")

    try:
        driver.get(URL)

        # 2. Tratamento de Cookies (ID: onetrust-accept-btn-handler)
        cookie_button_id = "onetrust-accept-btn-handler"
        try:
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, cookie_button_id))
            )
            cookie_button.click()
            print("Cookies aceitos com sucesso.")
            time.sleep(2) # Aumentar ligeiramente a espera após aceitar cookies
        except TimeoutException:
            print("Botão de cookies não encontrado ou já aceito. Continuando...")
        except Exception as e_cookie:
            print(f"Erro inesperado ao tratar cookies: {e_cookie}. Continuando...")

        # 3. Esperar e selecionar 'All' para a paginação
        pagination_dropdown_selector = "div.Pagination_content__f2at7 select"

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, pagination_dropdown_selector))
            )
            print("Dropdown de paginação encontrado. Tentando selecionar 'All'...")
            
            retries = 3
            selected = False
            while retries > 0 and not selected:
                try:
                    select_element = driver.find_element(By.CSS_SELECTOR, pagination_dropdown_selector)
                    select = Select(select_element)
                    select.select_by_value("-1") 
                    print("Opção 'All' selecionada. Aguardando o carregamento de todos os registros...")
                    time.sleep(7) 
                    selected = True
                except (NoSuchElementException, StaleElementReferenceException) as e_select:
                    print(f"Tentativa {4-retries}: Erro ao encontrar/selecionar o dropdown ({e_select}). Tentando novamente...")
                    retries -= 1
                    time.sleep(3)
                except Exception as e_general_select:
                     print(f"Erro inesperado ao selecionar 'All': {e_general_select}. Prosseguindo...")
                     break # Sai do loop se for um erro diferente

            if not selected and retries == 0:
                 print("Não foi possível selecionar 'All' após várias tentativas. Prosseguindo com os dados visíveis.")

        except TimeoutException:
             print("Dropdown de paginação não encontrado após 20 segundos. Prosseguindo...")


        # 4. Extrair a Tabela com Pandas
        table_css_selector = "table.Crom_table__p1iZz"

        try:
            table_element = WebDriverWait(driver, 15).until( # Aumentar espera pela tabela
                EC.presence_of_element_located((By.CSS_SELECTOR, table_css_selector))
            )

            # Usar JavaScript para garantir que a tabela esteja visível
            driver.execute_script("arguments[0].scrollIntoView(true);", table_element)
            time.sleep(1)

            html_content = table_element.get_attribute('outerHTML')
            tables = pd.read_html(html_content)

            if tables:
                df = tables[0]
                if not df.empty:
                    all_records_df = pd.concat([all_records_df, df], ignore_index=True)
                    print(f"Dados brutos extraídos. Total de linhas: {len(all_records_df)}")

                    # 5. Limpeza e Exportação

                    # 5.1. Renomear e limpar a coluna de Rank (se existir)
                    if 'Unnamed: 0' in all_records_df.columns:
                        all_records_df = all_records_df.rename(columns={'Unnamed: 0': 'RANK'})

                    # 5.2. FILTRAGEM CRUCIAL: Remove colunas que terminam com ' RANK' (com espaço antes)
                    cols_to_keep = [col for col in all_records_df.columns
                                    if not (isinstance(col, str) and col.strip().endswith(' RANK'))]

                    # Verifica se cols_to_keep não está vazio
                    if not cols_to_keep:
                         print("Erro: Nenhuma coluna mantida após a filtragem. Verifique os nomes das colunas.")
                         df_final = all_records_df # Mantém o DF original se a filtragem falhar
                    elif set(cols_to_keep) == set(all_records_df.columns):
                         print("Nenhuma coluna 'RANK' encontrada para remover.")
                         df_final = all_records_df
                    else:
                        print(f"Colunas removidas: {set(all_records_df.columns) - set(cols_to_keep)}")
                        df_final = all_records_df[cols_to_keep]


                    # 5.3. Remover linhas completamente nulas
                    df_final = df_final.dropna(how='all')

                    # 5.4. Converte e salva no JSON
                    data_json = df_final.to_json(orient='records', indent=4, force_ascii=False) # Adicionado force_ascii=False

                    with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                        f.write(data_json)

                    print(f"\n--- SUCESSO SCRAPER 1 ---")
                    print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
                    print(f"Total de registros exportados: {len(df_final)}")

                else:
                    print("DataFrame extraído da tabela está vazio.")
            else:
                print("Nenhuma tabela de stats de jogadores encontrada com o seletor.")

        except TimeoutException:
            print("Tabela de jogadores não encontrada após 15 segundos.")
        except Exception as e_table:
            print(f"Erro ao extrair ou processar a tabela: {e_table}")

    except Exception as e:
        print(f"\n--- ERRO CRÍTICO SCRAPER 1 ---")
        print(f"Ocorreu um erro geral: {e}")


def scraper_basketball_reference_schedule(driver):
    """
    Método 2: Scraper Basketball-Reference Schedule
    Endpoint: https://www.basketball-reference.com/leagues/NBA_2026_games-october.html
    """
    BASE_URL = "https://www.basketball-reference.com"
    START_URL = f"{BASE_URL}/leagues/NBA_2026_games-october.html"
    JSON_FILENAME = "nba_2026_schedule_completo.json"
    all_games_df = pd.DataFrame()

    print("\n\n" + "=" * 50)
    print("INICIANDO SCRAPER 2: BASKETBALL-REFERENCE SCHEDULE")
    print(f"Acessando o endpoint inicial: {START_URL}")

    try:
        driver.get(START_URL)

        # 1. Esperar pelo carregamento dos filtros de mês
        filter_div_selector = "div.filter"
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, filter_div_selector))
            )
        except TimeoutException:
            print("Filtros de mês não encontrados. Verifique a URL ou a estrutura da página.")
            return # Sai da função se não encontrar os filtros

        # Procurar todos os links de meses
        month_links = driver.find_elements(By.CSS_SELECTOR, f"{filter_div_selector} a")

        # Criar uma lista de URLs a visitar, incluindo o mês atual (se for um link válido)
        urls_to_scrape = []
        try: # Adiciona tratamento de erro caso o span não exista
            current_month_link = driver.find_element(By.CSS_SELECTOR, f"{filter_div_selector} div > span") # Mês atual pode ser um span
            if current_month_link:
                 current_path = driver.current_url.split('/')[-1]
                 if "games-" in current_path:
                     urls_to_scrape.append(driver.current_url)
        except NoSuchElementException:
             print("Span do mês atual não encontrado, usando URL atual se aplicável.")
             current_path = driver.current_url.split('/')[-1]
             if "games-" in current_path and driver.current_url not in urls_to_scrape:
                 urls_to_scrape.append(driver.current_url)

        for link in month_links:
            href = link.get_attribute("href")
            # Garante que só peguemos links válidos de meses
            if href and "games-" in href and href not in urls_to_scrape:
                urls_to_scrape.append(href)

        # Define a ordem correta dos meses da temporada da NBA
        month_order = ['october', 'november', 'december', 'january', 'february', 'march', 'april', 'may', 'june']

        def get_month_from_url(url):
            try:
                return url.split('-')[-1].split('.')[0].lower()
            except:
                return None 

        urls_to_scrape = sorted(
            list(set(urls_to_scrape)),
            key=lambda url: month_order.index(get_month_from_url(url)) if get_month_from_url(url) in month_order else float('inf')
        )

        print(f"URLs de meses encontradas e ordenadas: {urls_to_scrape}")


        # 2. Iterar sobre cada URL de mês para extrair a tabela
        for url in urls_to_scrape:
            month_name = get_month_from_url(url).capitalize() if get_month_from_url(url) else "Desconhecido"
            print(f"\n--> Coletando dados para o mês: {month_name}")

            if url != driver.current_url:
                try:
                    driver.get(url)
                    time.sleep(2) 
                except Exception as e_nav:
                     print(f"   -> Erro ao navegar para {url}: {e_nav}")
                     continue # Pula para o próximo mês se a navegação falhar

            # Esperar que a tabela seja recarregada
            table_css_selector = "table#schedule" # Usando o ID da tabela
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, table_css_selector))
                )

                # Garante que o elemento está pronto antes de tentar o read_html
                table_element = driver.find_element(By.CSS_SELECTOR, table_css_selector)
                html_content = table_element.get_attribute('outerHTML')


                tables = pd.read_html(html_content)

                if tables:
                    df_month = tables[0]
                    df_month['Month'] = month_name

                    if 'Date' in df_month.columns:
                       df_month = df_month[df_month['Date'] != 'Date']

                    all_games_df = pd.concat([all_games_df, df_month], ignore_index=True)
                    print(f"   -> {len(df_month)} jogos adicionados. Total: {len(all_games_df)}")

            except (TimeoutException, StaleElementReferenceException) as e_table:
                print(f"   -> Erro ao carregar ou processar a tabela para {month_name}: {e_table}")
                if isinstance(e_table, StaleElementReferenceException):
                    print("   -> Tentando novamente após StaleElementReferenceException...")
                    time.sleep(3)
                    try:
                       table_element = driver.find_element(By.CSS_SELECTOR, table_css_selector)
                       html_content = table_element.get_attribute('outerHTML')
                       tables = pd.read_html(html_content)
                       if tables:
                            df_month = tables[0]
                            df_month['Month'] = month_name
                            if 'Date' in df_month.columns:
                                df_month = df_month[df_month['Date'] != 'Date']
                            all_games_df = pd.concat([all_games_df, df_month], ignore_index=True)
                            print(f"   -> RE-TENTATIVA SUCESSO: {len(df_month)} jogos adicionados. Total: {len(all_games_df)}")
                    except Exception as e_retry:
                        print(f"   -> RE-TENTATIVA FALHOU para {month_name}: {e_retry}")
                continue # Continua para o próximo mês se der erro
            except Exception as e_general_table:
                 print(f"   -> Erro inesperado ao processar {month_name}: {e_general_table}")
                 continue


        # 3. Limpeza e Exportação Final
        if not all_games_df.empty:
            df_final = all_games_df.copy()

            df_final = df_final.drop(columns=['Unnamed: 6'])

            pts_cols = [col for col in df_final.columns if 'PTS' in col]
            if len(pts_cols) >= 2:
                 # Assume que a primeira coluna PTS é do visitante e a segunda do mandante
                 new_names = {'PTS': 'Visitor PTS', 'PTS.1': 'Home PTS', 'Unnamed: 7': 'Overtime'}
                 if 'Unnamed: 3' in df_final.columns and 'PTS' in df_final.columns and 'PTS.1' not in df_final.columns:
                      new_names = {'Unnamed: 3': 'Visitor PTS', 'PTS': 'Home PTS'}
                 df_final.rename(columns=new_names, inplace=True)
                 print(f"Colunas PTS renomeadas para: {new_names}")
            else:
                 print("Não foi possível identificar e renomear as colunas PTS corretamente.")

            data_json = df_final.to_json(orient='records', indent=4, force_ascii=False)

            with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                f.write(data_json)

            print(f"\n--- SUCESSO SCRAPER 2 ---")
            print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
            print(f"Total de jogos exportados: {len(df_final)}")

        else:
            print("Nenhum dado de agendamento foi coletado.")

    except Exception as e:
        print(f"\n--- ERRO CRÍTICO SCRAPER 2 ---")
        print(f"Ocorreu um erro geral: {e}")


def scraper_espn_standings(driver):
    """
    Método 3: Scraper ESPN Standings (Classificação) - Coleta todas as temporadas.
    Endpoint: https://www.espn.com.br/nba/classificacao
    """
    START_URL = "https://www.espn.com.br/nba/classificacao" 
    JSON_FILENAME = "nba_espn_standings_all_seasons.json" 
    all_standings_df = pd.DataFrame()
    base_espn_url = "https://www.espn.com.br" 

    print("\n\n" + "=" * 50)
    print("INICIANDO SCRAPER 3: ESPN NBA STANDINGS (TODAS AS TEMPORADAS)")
    print(f"Acessando o endpoint inicial: {START_URL}")

    try:
        driver.get(START_URL)
        time.sleep(3)

        # 1. Tratamento de Cookies (se necessário)
        cookie_button_id = "onetrust-accept-btn-handler"
        try:
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, cookie_button_id))
            )
            cookie_button.click()
            print("Cookies aceitos com sucesso.")
            time.sleep(2)
        except TimeoutException:
            print("Botão de cookies não encontrado ou já aceito. Continuando...")
        except Exception as e_cookie:
             print(f"Erro ao tratar cookies: {e_cookie}. Continuando...")

        # 2. Encontrar o dropdown de temporadas e extrair URLs
        season_urls = []
        season_dropdown_selector = "div.dropdown select[name*='::']"
        try:
            season_dropdown_elements = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, season_dropdown_selector))
            )
            # Tenta encontrar o dropdown correto (geralmente o primeiro que contém anos)
            select_element = None
            for dropdown in season_dropdown_elements:
                 options_text = [opt.text for opt in Select(dropdown).options]
                 if any(re.search(r'\d{4}', text) for text in options_text): # Verifica se há anos nas opções
                      select_element = dropdown
                      break

            if not select_element:
                 print("Dropdown de temporada com anos não encontrado.")
                 raise NoSuchElementException("Dropdown de temporada não encontrado com o seletor esperado.")


            select = Select(select_element)
            options = select.options

            # Pega a URL da temporada atual (geralmente a selecionada por padrão)
            current_url = driver.current_url.split('?')[0].split('#')[0] 
             # Garante que a URL base não termine com '/' para evitar '//'
            if current_url.endswith('/'):
                current_url = current_url[:-1]
            # Adiciona a URL base se ainda não estiver na lista (para a temporada atual)
            if START_URL not in season_urls:
                 season_urls.append(START_URL)


            for option in options:
                data_url = option.get_attribute('data-url')
                if data_url and data_url.startswith('/'): # Verifica se é um caminho relativo
                     full_url = base_espn_url + data_url
                     if full_url not in season_urls:
                        season_urls.append(full_url)
                elif data_url and data_url.startswith('http'): # Se for URL completa
                     if data_url not in season_urls:
                          season_urls.append(data_url)


            print(f"Encontradas {len(season_urls)} URLs de temporadas para raspar.")

        except (TimeoutException, NoSuchElementException) as e_dropdown:
            print(f"Dropdown de temporadas não encontrado ou erro ao processar: {e_dropdown}.")
            print("Tentando raspar apenas a temporada atual.")
            if not season_urls: # Se a lista ainda estiver vazia, adiciona a URL atual
                 season_urls.append(driver.current_url)
        except Exception as e_general_dropdown:
             print(f"Erro inesperado ao buscar URLs de temporada: {e_general_dropdown}")
             if not season_urls:
                  season_urls.append(driver.current_url)


        # 3. Iterar sobre cada URL de temporada
        for url in season_urls:
            try:
                # Extrai o ano/formato da temporada da URL ou do texto do dropdown
                season_year_str = "Atual"
                season_match = re.search(r'/temporada/(\d{4})', url)
                if season_match:
                    year = int(season_match.group(1))
                    season_year_str = f"{year-1}-{str(year)[-2:]}" # Formato 2024-25
                elif url == START_URL: # Se for a URL base, tenta pegar do dropdown
                     try:
                          # Garante que 'select' foi definido
                          if 'select' in locals() or 'select' in globals():
                              selected_option_text = select.first_selected_option.text
                              if re.match(r'\d{4}-\d{2}', selected_option_text): 
                                   season_year_str = selected_option_text
                              elif re.match(r'\d{4}', selected_option_text): # Se for só o ano final 2026
                                   year_end = int(selected_option_text)
                                   season_year_str = f"{year_end-1}-{str(year_end)[-2:]}"
                          else:
                              print("Dropdown 'select' não definido, usando 'Atual' para a temporada.")
                     except Exception as e_year_extract:
                          print(f"Erro ao extrair ano do texto do dropdown: {e_year_extract}, usando 'Atual'.")


                print(f"\n--> Coletando dados para a temporada: {season_year_str} (URL: {url})")

                if url != driver.current_url:
                    print(f"    Navegando para: {url}")
                    driver.get(url)
                    time.sleep(4) 

                # 4. Esperar e extrair as tabelas da temporada atual
                data_table_selector = "div.Table__Scroller > table.Table" 
                fixed_left_table_selector = "table.Table--fixed-left" 

                try:
                    # Espera pelas tabelas de dados (direita)
                    data_table_elements = WebDriverWait(driver, 20).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, data_table_selector))
                    )
                    # Espera pelas tabelas de nomes (esquerda)
                    name_table_elements = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, fixed_left_table_selector))
                    )

                    # Filtra para pegar apenas as tabelas de conferência (geralmente as duas primeiras de cada tipo)
                    if len(data_table_elements) >= 2 and len(name_table_elements) >= 2:
                        # As tabelas de dados (data) são as que estão dentro do Scroller
                        data_tables_to_process = data_table_elements[:2]
                        # As tabelas de nome (name) são as 'fixed-left'
                        name_tables_to_process = name_table_elements[:2]
                    else:
                         print(f"   -> Número inesperado de tabelas encontrado para {season_year_str}. Pulando.")
                         continue

                except TimeoutException:
                    print(f"   -> Tabelas não encontradas para a temporada {season_year_str} com os seletores. Pulando...")
                    continue # Pula para a próxima temporada


                print(f"   -> Encontradas {len(data_tables_to_process)} tabelas de dados e {len(name_tables_to_process)} de nomes. Processando...")

                # 5. Ler tabelas com Pandas, limpar e combinar
                df_list_combined = []
                conference_names = ['Eastern', 'Western']

                for i in range(len(data_tables_to_process)): # Itera sobre 0 e 1 (Leste e Oeste)
                    try:
                        # --- MODIFICAÇÃO INICIADA ---
                        # Pega a tabela de nomes (esquerda)
                        name_table_element = name_tables_to_process[i]

                        # Extrai os nomes das equipes usando Selenium
                        # O seletor "span.hide-mobile > a.AnchorLink" pega o nome completo da equipe, com base no HTML
                        team_name_elements = name_table_element.find_elements(By.CSS_SELECTOR, "span.hide-mobile > a.AnchorLink")
                        
                        team_names = [elem.text for elem in team_name_elements if elem.text]

                        if not team_names:
                             print(f"   -> Aviso: Nenhum nome de equipe encontrado com o seletor 'span.hide-mobile > a.AnchorLink' para Conf. {i+1}, {season_year_str}.")
                             # Fallback: Tentar um seletor mais genérico se o primeiro falhar, baseado no seu HTML
                             team_name_elements = name_table_element.find_elements(By.CSS_SELECTOR, "a.AnchorLink[data-clubhouse-uid]")
                             team_names = [elem.text for elem in team_name_elements if elem.text]
                             # Remove duplicatas se o seletor genérico pegar a abreviação e o nome
                             unique_names = []
                             for name in team_names:
                                 if name not in unique_names:
                                     unique_names.append(name)
                             # Filtra as abreviações (ex: "NY") e mantém apenas nomes longos
                             team_names = [name for name in unique_names if len(name) > 3] 
                             print(f"   -> Fallback: Encontrados {len(team_names)} nomes com 'a.AnchorLink[data-clubhouse-uid]'")


                        if not team_names:
                             print(f"   -> ERRO: Não foi possível extrair nomes de equipes para Conf. {i+1}, {season_year_str}. Pulando.")
                             continue

                        df_names = pd.DataFrame(team_names, columns=['Equipe'])
                        
                        # Remove linhas de cabeçalho residuais que possam ter apenas o nome da conferência
                        df_names = df_names[~df_names['Equipe'].astype(str).str.contains('CONFERÊNCIA|EASTERN|WESTERN', na=False, case=False, regex=True)]
                
                        data_html = data_tables_to_process[i].get_attribute('outerHTML')
                        df_data = pd.read_html(data_html)[0] # REMOVIDO StringIO

                        # Limpar MultiIndex se houver na tabela de dados
                        if isinstance(df_data.columns, pd.MultiIndex):
                            df_data.columns = df_data.columns.map(''.join).str.strip()

                         # Remove a linha de cabeçalho duplicada (ex: V, D, % Vit.) que o read_html pode incluir
                        df_data = df_data[~df_data[df_data.columns[0]].astype(str).str.fullmatch(df_data.columns[0], case=False, na=False)]


                        # Verifica se o número de linhas corresponde (após limpeza inicial)
                        if len(df_names) != len(df_data):
                            print(f"   -> Aviso: Discrepância no número de linhas entre nomes ({len(df_names)}) e dados ({len(df_data)}) para Conf. {i+1}, {season_year_str}. Tentando alinhar...")
                            df_names_cleaned = df_names.dropna(how='all').reset_index(drop=True)
                            df_data_cleaned = df_data.dropna(how='all').reset_index(drop=True)
                            if len(df_names_cleaned) == len(df_data_cleaned):
                                 print("    -> Alinhamento bem-sucedido após remover linhas vazias.")
                                 df_names = df_names_cleaned
                                 df_data = df_data_cleaned
                            else:
                                 print(f"   -> ERRO: Não foi possível alinhar tabelas para Conf. {i+1}, {season_year_str}. Pulando esta conferência.")
                                 print(f"Nomes ({len(df_names_cleaned)}):", df_names_cleaned['Equipe'].tolist()) # Para depuração
                                 print(f"Dados ({len(df_data_cleaned)}):", df_data_cleaned.head().to_string()) # Para depuração
                                 continue # Pula para a próxima conferência/temporada

                        # Adiciona reset_index(drop=True) para garantir alinhamento correto
                        df_combined = pd.concat([df_names.reset_index(drop=True), df_data.reset_index(drop=True)], axis=1)

                        # Adicionar colunas de Conferência e Temporada
                        df_combined['Conference'] = conference_names[i]
                        df_combined['Season'] = season_year_str 
                        df_list_combined.append(df_combined)

                    except Exception as e_proc_table:
                         print(f"   -> Erro ao processar tabela {i+1} para {season_year_str}: {e_proc_table}")


                # Concatena os DFs da temporada atual (Leste e Oeste combinados)
                if df_list_combined:
                     df_season = pd.concat(df_list_combined, ignore_index=True)
                     all_standings_df = pd.concat([all_standings_df, df_season], ignore_index=True)
                     print(f"   -> {len(df_season)} times adicionados para {season_year_str}. Total geral: {len(all_standings_df)}")

            except Exception as e_season_loop:
                 print(f"Erro no loop da temporada {season_year_str} (URL: {url}): {e_season_loop}")
                 continue # Continua para a próxima temporada em caso de erro

        # 6. Limpeza e Exportação Final (após coletar todas as temporadas)
        if not all_standings_df.empty:
            df_final = all_standings_df.dropna(subset=['Equipe'], how='all')
            df_final = df_final[df_final['Equipe'] != ''] 

            # Reordena colunas para ter Season e Conference primeiro
            cols_order = ['Season', 'Conference', 'Equipe']
            remaining_cols = [col for col in df_final.columns if col not in cols_order]
            df_final = df_final[cols_order + remaining_cols]

            data_json = df_final.to_json(orient='records', indent=4, force_ascii=False) # Adicionado force_ascii=False

            with open(JSON_FILENAME, 'w', encoding='utf-8') as f:
                f.write(data_json)

            print(f"\n--- SUCESSO SCRAPER 3 ---")
            print(f"Dados exportados para o arquivo: {JSON_FILENAME}")
            print(f"Total de registros (times * temporadas) exportados: {len(df_final)}")

        else:
            print("Nenhuma tabela de classificação encontrada em nenhuma temporada.")

    except Exception as e:
        print(f"\n--- ERRO CRÍTICO SCRAPER 3 ---")
        print(f"Ocorreu um erro geral: {e}")


# --- EXECUÇÃO PRINCIPAL ---

# Inicializa o driver
driver = setup_driver()

if driver:
    scraper_nba_stats(driver) 
    scraper_basketball_reference_schedule(driver) 
    scraper_espn_standings(driver)
    print("\nFechando o navegador...")
    driver.quit()
    print("Navegador fechado.")
else:
    print("Não foi possível inicializar o WebDriver. O script será encerrado.")

