# TEGD-nba-scrapping

## Descrição
Projeto desenvolvido para a disciplina de Tópicos Especiais em Gerência de Dados do curso de Sistemas de Informação, UFSC. O objetivo do projeto é coletar, processar e analisar dados estatísticos da NBA utilizando técnicas de web scraping e inteligência artificial.

## Funcionalidades
- Coleta de dados estatísticos da NBA para a temporada 2025-26.
- Processamento e análise dos dados coletados.
- Assistente virtual baseado em IA para responder perguntas sobre os dados da NBA.

## Tecnologias Utilizadas
- Python
- Bibliotecas: requests, BeautifulSoup, pandas, tkinter, openai
- API OpenAI para integração com modelos de linguagem avançados.

## Instruções de Uso
1. Clone o repositório:
   ```bash
   git clone https://github.com/BrunoDdeBorja/TEGD-nba-scrapping.git
    ```

2. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o scrapping para coletar os dados da NBA:
   ```bash
   python main.py
   ```

3. Configure sua chave de API da OpenAI no arquivo `nba_assistente.py`.

4. Execute o assistente virtual:
   ```bash
   python nba_assistente.py
   ```
5. Utilize a interface gráfica para fazer perguntas sobre os dados da NBA.
