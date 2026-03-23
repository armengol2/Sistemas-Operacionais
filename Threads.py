import random
import threading
import time

try:
    from rich.console import Console
    from rich.console import Group
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table

    RICH_DISPONIVEL = True
except ImportError:
    RICH_DISPONIVEL = False


if RICH_DISPONIVEL:
    CONSOLE = Console(force_terminal=True)
else:
    CONSOLE = None


EMPRESAS_INICIAIS = [
    ("Petrobras", 100.0),
    ("Lockheed", 150.0),
    ("SigSauer", 120.0),
    ("Tag Heuer", 90.0),
    ("Volkswagen", 100.0),
    ("Banco master", 200.0),
]

FITA_ORDENS = []
PAINEL_TRADERS = {}


class Mercado:
    def __init__(self, preco_inicial, nome):
        self.nome = nome
        self.preco_inicial = preco_inicial
        self.preco_atual = preco_inicial
        self.maior_valor = self.preco_atual
        self.menor_valor = self.preco_atual
        self.ativo_valido = True
        self.ultimo_trader = "ABERTURA"
        self.ultima_acao = "LISTADA"
        self.ultima_quantidade = 0
        self.historico_precos = [self.preco_atual]

    def comprar(self, trader_nome, quantidade):
        if not self.ativo_valido:
            return

        self.preco_atual += 0.1 * quantidade

        if self.preco_atual > self.maior_valor:
            self.maior_valor = self.preco_atual

        self.ultimo_trader = trader_nome
        self.ultima_acao = "COMPRA"
        self.ultima_quantidade = quantidade
        self.historico_precos.append(self.preco_atual)
        self.historico_precos = self.historico_precos[-18:]

        registrar_ordem(
            trader_nome,
            self.nome,
            "COMPRA",
            quantidade,
            self.preco_atual,
            "green",
        )
        registrar_trader(trader_nome, "COMPRA", quantidade)

    def vender(self, trader_nome, quantidade):
        if not self.ativo_valido:
            return

        self.preco_atual -= 0.1 * quantidade

        if self.preco_atual <= 0:
            self.preco_atual = 0
            self.ativo_valido = False
            self.ultimo_trader = trader_nome
            self.ultima_acao = "FALIU"
            self.ultima_quantidade = quantidade
            self.historico_precos.append(self.preco_atual)
            self.historico_precos = self.historico_precos[-18:]
            registrar_ordem(
                trader_nome,
                self.nome,
                "QUEBROU",
                quantidade,
                self.preco_atual,
                "bold red",
            )
            registrar_trader(trader_nome, "VENDA", quantidade)
        else:
            self.ultimo_trader = trader_nome
            self.ultima_acao = "VENDA"
            self.ultima_quantidade = quantidade
            self.historico_precos.append(self.preco_atual)
            self.historico_precos = self.historico_precos[-18:]
            registrar_ordem(
                trader_nome,
                self.nome,
                "VENDA",
                quantidade,
                self.preco_atual,
                "red",
            )
            registrar_trader(trader_nome, "VENDA", quantidade)

        if self.preco_atual < self.menor_valor:
            self.menor_valor = self.preco_atual


def registrar_ordem(trader_nome, mercado_nome, acao, quantidade, preco, estilo):
    horario = time.strftime("%H:%M:%S")
    mensagem = f"{horario} | {trader_nome:<8} | {acao:<7} | {mercado_nome:<12} | {quantidade:>4} | R${preco:>7.2f}"
    FITA_ORDENS.append((mensagem, estilo))
    del FITA_ORDENS[:-12]

    if not RICH_DISPONIVEL:
        print(mensagem)


def registrar_trader(trader_nome, acao, quantidade):
    trader = PAINEL_TRADERS.setdefault(
        trader_nome,
        {"operacoes": 0, "compras": 0, "vendas": 0, "volume": 0},
    )
    trader["operacoes"] += 1
    trader["volume"] += quantidade

    if acao == "COMPRA":
        trader["compras"] += 1
    else:
        trader["vendas"] += 1


def acao_trader(nome, lista_mercados, rodadas):
    rodada_atual = 0

    while rodada_atual < rodadas:
        mercado_alvo = random.choice(lista_mercados)
        if mercado_alvo.ativo_valido:
            acao = random.choice(["comprar", "vender"])
            quantidade = random.randint(1, 100)

            if acao == "comprar":
                mercado_alvo.comprar(nome, quantidade)
            else:
                mercado_alvo.vender(nome, quantidade)

        time.sleep(random.uniform(0.1, 0.5))
        rodada_atual += 1


def painel_mercado(mercados):
    tabela = Table(expand=True)
    tabela.add_column("Empresa", justify="left")
    tabela.add_column("St", justify="center")
    tabela.add_column("Preco", justify="right")
    tabela.add_column("Valoriz.", justify="right")
    tabela.add_column("Faixa", justify="right")
    tabela.add_column("Ultima", justify="left")

    for mercado in mercados:
        status = "[green]ATIVA[/green]" if mercado.ativo_valido else "[red]FALIU[/red]"
        valorizacao = ((mercado.preco_atual - mercado.preco_inicial) / mercado.preco_inicial) * 100

        if valorizacao > 0:
            valorizacao_texto = f"[green]+{valorizacao:.1f}%[/green]"
        elif valorizacao < 0:
            valorizacao_texto = f"[red]{valorizacao:.1f}%[/red]"
        else:
            valorizacao_texto = "[yellow]0.0%[/yellow]"

        tabela.add_row(
            mercado.nome,
            status,
            f"R${mercado.preco_atual:.2f}",
            valorizacao_texto,
            f"R${mercado.menor_valor:.0f}/R${mercado.maior_valor:.0f}",
            f"{mercado.ultimo_trader}/{mercado.ultima_acao[:1]} {mercado.ultima_quantidade}",
        )

    return Panel(tabela, title="Mesa de Operacoes", border_style="cyan")


def painel_traders():
    tabela = Table(expand=True)
    tabela.add_column("Trader", justify="left")
    tabela.add_column("Ops", justify="right")
    tabela.add_column("Compras", justify="right")
    tabela.add_column("Vendas", justify="right")
    tabela.add_column("Volume", justify="right")

    ranking = sorted(
        PAINEL_TRADERS.items(),
        key=lambda item: (item[1]["operacoes"], item[1]["volume"]),
        reverse=True,
    )

    for trader_nome, dados in ranking:
        tabela.add_row(
            trader_nome,
            str(dados["operacoes"]),
            str(dados["compras"]),
            str(dados["vendas"]),
            str(dados["volume"]),
        )

    return Panel(tabela, title="Traders Ativos", border_style="magenta")


def painel_fita():
    if not FITA_ORDENS:
        return Panel("Aguardando primeiras ordens...", title="Fita de Ordens", border_style="yellow")

    linhas = []
    for mensagem, estilo in reversed(FITA_ORDENS[-10:]):
        linhas.append(f"[{estilo}]{mensagem}[/{estilo}]")

    return Panel(Group(*linhas), title="EM EXECUÇÃO", border_style="yellow")


def painel_resumo(mercados, nomes_traders, rodadas, inicio):
    ativos = sum(1 for mercado in mercados if mercado.ativo_valido)
    falidas = len(mercados) - ativos
    total_operacoes = sum(dados["operacoes"] for dados in PAINEL_TRADERS.values())
    volume_total = sum(dados["volume"] for dados in PAINEL_TRADERS.values())
    alvo_operacoes = len(nomes_traders) * rodadas
    tempo_decorrido = time.time() - inicio
    empresas_vivas = [mercado.preco_atual for mercado in mercados if mercado.ativo_valido]

    grade = Table.grid(padding=(0, 1))
    grade.add_row("Tempo", f"{tempo_decorrido:5.1f}s")
    grade.add_row("Ativas", f"{ativos}")
    grade.add_row("Falidas", f"{falidas}")
    grade.add_row("Ordens", f"{total_operacoes}/{alvo_operacoes}")
    grade.add_row("Volume", f"{volume_total}")
    if empresas_vivas:
        grade.add_row("Media ativa", f"R${sum(empresas_vivas) / len(empresas_vivas):.2f}")
    else:
        grade.add_row("Media ativa", "R$0.00")

    return Panel(grade, title="Resumo", border_style="green")


def montar_dashboard(mercados, nomes_traders, rodadas, inicio):
    layout = Layout()
    layout.split_column(
        Layout(name="superior", ratio=3),
        Layout(name="inferior", ratio=2),
    )
    layout["superior"].split_row(
        Layout(name="mercado", ratio=3),
        Layout(name="traders", ratio=2),
    )
    layout["inferior"].split_row(
        Layout(name="fita", ratio=3),
        Layout(name="resumo", ratio=1),
    )

    layout["mercado"].update(painel_mercado(mercados))
    layout["traders"].update(painel_traders())
    layout["fita"].update(painel_fita())
    layout["resumo"].update(painel_resumo(mercados, nomes_traders, rodadas, inicio))
    return layout


def resumo_final(mercados):
    tabela = Table(expand=True)
    tabela.add_column("Empresa", justify="left")
    tabela.add_column("Status", justify="center")
    tabela.add_column("Preco final", justify="right")
    tabela.add_column("Minimo", justify="right")
    tabela.add_column("Maximo", justify="right")

    for mercado in mercados:
        status = "[green]ATIVA[/green]" if mercado.ativo_valido else "[red]FALIU[/red]"
        tabela.add_row(
            mercado.nome,
            status,
            f"R${mercado.preco_atual:.2f}",
            f"R${mercado.menor_valor:.2f}",
            f"R${mercado.maior_valor:.2f}",
        )

    return tabela


if __name__ == "__main__":
    mercados = [Mercado(preco_inicial, nome) for nome, preco_inicial in EMPRESAS_INICIAIS]
    nomes_traders = ["Jonas", "Breno", "Soned", "Estevan", "Mosca", "Ynoguti", "Renan"]
    PAINEL_TRADERS = {
        nome: {"operacoes": 0, "compras": 0, "vendas": 0, "volume": 0}
        for nome in nomes_traders
    }
    inicio_pregao = time.time()

    print("EMPRESAS CARREGADAS:")
    for nome, preco_inicial in EMPRESAS_INICIAIS:
        print(f"- {nome}: R${preco_inicial:.2f}")
    print("=" * 64)

    rodadas = int(input("quantidade de rodadas: "))
    threads = []

    for nome in nomes_traders:
        trader = threading.Thread(target=acao_trader, args=(nome, mercados, rodadas))
        threads.append(trader)
        trader.start()

    if RICH_DISPONIVEL:
        with Live(
            montar_dashboard(mercados, nomes_traders, rodadas, inicio_pregao),
            refresh_per_second=8,
            console=CONSOLE,
        ) as live:
            while any(trader.is_alive() for trader in threads):
                live.update(montar_dashboard(mercados, nomes_traders, rodadas, inicio_pregao))
                time.sleep(0.1)

            live.update(montar_dashboard(mercados, nomes_traders, rodadas, inicio_pregao))
    else:
        while any(trader.is_alive() for trader in threads):
            time.sleep(0.1)

    if RICH_DISPONIVEL:
        CONSOLE.print("\n[bold cyan]MERCADO FECHADO[/bold cyan]")
        CONSOLE.print(resumo_final(mercados))
    else:
        print("MERCADO FECHADO")
        print("=" * 45)
        for mercado in mercados:
            print(f"Empresa: {mercado.nome}")
            print(f"Status: {'ATIVA' if mercado.ativo_valido else 'FALIU'}")
            print(f"Preco Final: R${mercado.preco_atual:.2f}")
            print(f"Menor Valor: R${mercado.menor_valor:.2f}")
            print(f"Maior Valor: R${mercado.maior_valor:.2f}")
            print("-" * 45)
