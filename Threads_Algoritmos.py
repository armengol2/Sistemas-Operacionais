from dataclasses import dataclass
import random
import time
from typing import List, Optional, Tuple

try:
    from rich.console import Console, Group
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


SEMENTE_PADRAO = 42
PASSO_ATUALIZACAO = 0.05


@dataclass(frozen=True)
class TraderProcesso:
    nome: str
    empresa_alvo: str
    tempo_chegada: float
    tempo_execucao: float


@dataclass
class ResultadoProcesso:
    nome: str
    empresa_alvo: str
    tempo_chegada: float
    tempo_execucao: float
    inicio: float
    fim: float
    espera: float


@dataclass
class ResultadoEscalonamento:
    algoritmo: str
    resultados: List[ResultadoProcesso]
    total_espera: float
    media_espera: float
    gantt: List[Tuple[str, float, float]]


@dataclass
class ProcessoEmExecucao:
    nome: str
    empresa_alvo: str
    inicio: float
    duracao: float


class Mercado:
    def __init__(self, nome: str, preco_inicial: float = 150.0):
        self.nome = nome
        self.preco_inicial = preco_inicial
        self.preco_atual = preco_inicial
        self.maior_valor = preco_inicial
        self.menor_valor = preco_inicial
        self.ativo_valido = True
        self.ultimo_trader = "ABERTURA"
        self.ultima_acao = "LISTADA"
        self.ultima_quantidade = 0


def formatar_tempo(valor: float) -> str:
    return f"{valor:.2f}s"


def barra_progresso(fracao: float, largura: int = 24) -> str:
    fracao = max(0.0, min(1.0, fracao))
    preenchido = int(fracao * largura)
    return "[" + "#" * preenchido + "-" * (largura - preenchido) + f"] {fracao * 100:5.1f}%"


def registrar_evento(eventos: List[str], mensagem: str, limite: int = 8) -> None:
    horario = time.strftime("%H:%M:%S")
    eventos.append(f"{horario} | {mensagem}")
    del eventos[:-limite]


def criar_mercados(quantidade_empresas: int) -> List[Mercado]:
    return [Mercado(f"Empresa_{indice + 1}") for indice in range(quantidade_empresas)]


def localizar_mercado(mercados: List[Mercado], nome_empresa: str) -> Mercado:
    for mercado in mercados:
        if mercado.nome == nome_empresa:
            return mercado
    return mercados[0]


def aplicar_operacao_mercado(
    mercados: List[Mercado],
    processo: TraderProcesso,
    rng: random.Random,
    eventos: List[str],
) -> None:
    if rng.random() < 0.7:
        mercado = localizar_mercado(mercados, processo.empresa_alvo)
    else:
        mercado = rng.choice(mercados)

    if not mercado.ativo_valido:
        registrar_evento(eventos, f"{processo.nome} tentou operar {mercado.nome}, mas ela ja faliu")
        return

    acao = rng.choice(["COMPRA", "VENDA"])
    quantidade = rng.randint(1, 35)

    if acao == "COMPRA":
        mercado.preco_atual += 0.1 * quantidade
        mercado.ultima_acao = "COMPRA"
        estilo_evento = f"{processo.nome} comprou {quantidade} de {mercado.nome}"
    else:
        mercado.preco_atual -= 0.1 * quantidade
        if mercado.preco_atual <= 0:
            mercado.preco_atual = 0
            mercado.ativo_valido = False
            mercado.ultima_acao = "FALIU"
            estilo_evento = f"{processo.nome} quebrou {mercado.nome} com venda de {quantidade}"
        else:
            mercado.ultima_acao = "VENDA"
            estilo_evento = f"{processo.nome} vendeu {quantidade} de {mercado.nome}"

    mercado.maior_valor = max(mercado.maior_valor, mercado.preco_atual)
    mercado.menor_valor = min(mercado.menor_valor, mercado.preco_atual)
    mercado.ultimo_trader = processo.nome
    mercado.ultima_quantidade = quantidade
    registrar_evento(eventos, f"{estilo_evento} | preco {mercado.preco_atual:.2f}")


def gerar_processos_tempo_real(
    quantidade_empresas: int,
    quantidade_traders: int,
    tempo_maximo_chegada: float,
    tempo_maximo_execucao: float,
    semente: int = SEMENTE_PADRAO,
) -> List[TraderProcesso]:
    rng = random.Random(semente)
    empresas = [f"Empresa_{indice + 1}" for indice in range(quantidade_empresas)]
    processos = []
    fator_empresas = 1.0 + min(0.12, quantidade_empresas / 1000.0)

    for indice in range(quantidade_traders):
        processos.append(
            TraderProcesso(
                nome=f"Trader_{indice + 1}",
                empresa_alvo=rng.choice(empresas),
                tempo_chegada=round(rng.uniform(0, max(0.0, tempo_maximo_chegada)), 2),
                tempo_execucao=round(
                    rng.uniform(0.2, max(0.2, tempo_maximo_execucao)) * fator_empresas,
                    2,
                ),
            )
        )

    return processos


def consolidar_resultado(
    algoritmo: str,
    resultados: List[ResultadoProcesso],
    gantt: List[Tuple[str, float, float]],
) -> ResultadoEscalonamento:
    total_espera = sum(item.espera for item in resultados)
    media_espera = total_espera / len(resultados)
    return ResultadoEscalonamento(
        algoritmo=algoritmo,
        resultados=resultados,
        total_espera=total_espera,
        media_espera=media_espera,
        gantt=gantt,
    )


def selecionar_processo(
    prontos: List[Tuple[int, TraderProcesso]],
    algoritmo: str,
) -> Tuple[int, TraderProcesso]:
    if algoritmo == "FCFS":
        return min(
            prontos,
            key=lambda item: (
                item[1].tempo_chegada,
                item[0],
            ),
        )

    return min(
        prontos,
        key=lambda item: (
            item[1].tempo_execucao,
            item[1].tempo_chegada,
            item[0],
        ),
    )


def registrar_chegadas(
    pendentes: List[Tuple[int, TraderProcesso]],
    proximo_indice: int,
    prontos: List[Tuple[int, TraderProcesso]],
    relogio: float,
    eventos: List[str],
) -> int:
    while (
        proximo_indice < len(pendentes)
        and pendentes[proximo_indice][1].tempo_chegada <= relogio
    ):
        indice_original, processo = pendentes[proximo_indice]
        prontos.append((indice_original, processo))
        registrar_evento(
            eventos,
            f"{processo.nome} chegou para operar {processo.empresa_alvo}",
        )
        proximo_indice += 1

    return proximo_indice


def montar_tabela_processos(processos: List[TraderProcesso]):
    tabela = Table(expand=True)
    tabela.add_column("Trader", justify="left")
    tabela.add_column("Empresa", justify="left")
    tabela.add_column("Chegada", justify="right")
    tabela.add_column("Execucao", justify="right")

    for processo in processos:
        tabela.add_row(
            processo.nome,
            processo.empresa_alvo,
            formatar_tempo(processo.tempo_chegada),
            formatar_tempo(processo.tempo_execucao),
        )

    return tabela


def montar_tabela_mercado(mercados: List[Mercado]) -> Table:
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

    return tabela


def montar_tabela_resultados(resultado: ResultadoEscalonamento):
    tabela = Table(expand=True)
    tabela.add_column("Trader", justify="left")
    tabela.add_column("Empresa", justify="left")
    tabela.add_column("Chegada", justify="right")
    tabela.add_column("Execucao", justify="right")
    tabela.add_column("Inicio", justify="right")
    tabela.add_column("Fim", justify="right")
    tabela.add_column("Espera", justify="right")

    for item in resultado.resultados:
        tabela.add_row(
            item.nome,
            item.empresa_alvo,
            formatar_tempo(item.tempo_chegada),
            formatar_tempo(item.tempo_execucao),
            formatar_tempo(item.inicio),
            formatar_tempo(item.fim),
            formatar_tempo(item.espera),
        )

    return tabela


def montar_tabela_fila(
    processos: List[TraderProcesso],
    titulo_vazio: str,
) -> Table:
    tabela = Table(expand=True)
    tabela.add_column("Trader", justify="left")
    tabela.add_column("Empresa", justify="left")
    tabela.add_column("Chegada", justify="right")
    tabela.add_column("Execucao", justify="right")

    if not processos:
        tabela.add_row(titulo_vazio, "-", "-", "-")
        return tabela

    for processo in processos:
        tabela.add_row(
            processo.nome,
            processo.empresa_alvo,
            formatar_tempo(processo.tempo_chegada),
            formatar_tempo(processo.tempo_execucao),
        )

    return tabela


def montar_tabela_finalizados(resultados: List[ResultadoProcesso]) -> Table:
    tabela = Table(expand=True)
    tabela.add_column("Trader", justify="left")
    tabela.add_column("Inicio", justify="right")
    tabela.add_column("Fim", justify="right")
    tabela.add_column("Espera", justify="right")

    if not resultados:
        tabela.add_row("Nenhum", "-", "-", "-")
        return tabela

    for item in resultados[-6:]:
        tabela.add_row(
            item.nome,
            formatar_tempo(item.inicio),
            formatar_tempo(item.fim),
            formatar_tempo(item.espera),
        )

    return tabela


def montar_painel_cpu(
    atual: Optional[ProcessoEmExecucao],
    relogio: float,
) -> Panel:
    if atual is None:
        conteudo = "Sem mais calculos por enquanto."
        return Panel(conteudo, title="CPU", border_style="red")

    tempo_decorrido = max(0.0, relogio - atual.inicio)
    progresso = tempo_decorrido / atual.duracao if atual.duracao > 0 else 1.0
    conteudo = (
        f"Trader: {atual.nome}\n"
        f"Empresa: {atual.empresa_alvo}\n"
        f"Inicio: {formatar_tempo(atual.inicio)}\n"
        f"Duracao prevista: {formatar_tempo(atual.duracao)}\n"
        f"Progresso: {barra_progresso(progresso)}"
    )
    return Panel(conteudo, title="CPU", border_style="green")


def montar_painel_resumo_parcial(
    algoritmo: str,
    relogio: float,
    quantidade_total: int,
    resultados: List[ResultadoProcesso],
    pendentes_restantes: int,
    mercados: List[Mercado],
) -> Panel:
    total_espera = sum(item.espera for item in resultados)
    media_espera = total_espera / len(resultados) if resultados else 0.0
    ativos = sum(1 for mercado in mercados if mercado.ativo_valido)
    falidas = len(mercados) - ativos
    conteudo = (
        f"Algoritmo: {algoritmo}\n"
        f"Relogio: {formatar_tempo(relogio)}\n"
        f"Concluidos: {len(resultados)}/{quantidade_total}\n"
        f"Empresas ativas: {ativos}\n"
        f"Empresas falidas: {falidas}\n"
        f"Aguardando chegada: {pendentes_restantes}\n"
        f"Soma parcial de espera: {formatar_tempo(total_espera)}\n"
        f"Media parcial de espera: {formatar_tempo(media_espera)}"
    )
    return Panel(conteudo, title="Resumo Parcial", border_style="cyan")


def montar_dashboard_simulacao(
    algoritmo: str,
    processos_base: List[TraderProcesso],
    mercados: List[Mercado],
    pendentes: List[Tuple[int, TraderProcesso]],
    proximo_indice: int,
    prontos: List[Tuple[int, TraderProcesso]],
    atual: Optional[ProcessoEmExecucao],
    resultados: List[ResultadoProcesso],
    eventos: List[str],
    inicio_simulacao: float,
):
    relogio = max(0.0, time.perf_counter() - inicio_simulacao)
    layout = Layout()
    layout.split_column(
        Layout(name="topo", ratio=3),
        Layout(name="baixo", ratio=2),
    )
    layout["topo"].split_row(
        Layout(name="cenario", ratio=2),
        Layout(name="status", ratio=2),
    )
    layout["baixo"].split_row(
        Layout(name="finalizados", ratio=2),
        Layout(name="eventos", ratio=2),
    )

    pendentes_visiveis = [item[1] for item in pendentes[proximo_indice:]]
    prontos_visiveis = [item[1] for item in prontos]
    grupo_status = Group(
        montar_painel_cpu(atual, relogio),
        montar_painel_resumo_parcial(
            algoritmo,
            relogio,
            len(processos_base),
            resultados,
            len(pendentes_visiveis),
            mercados,
        ),
        Panel(
            montar_tabela_fila(prontos_visiveis, "Fila vazia"),
            title="Fila de Prontos",
            border_style="yellow",
        ),
        Panel(
            montar_tabela_fila(pendentes_visiveis, "Sem chegadas futuras"),
            title="Aguardando Chegada",
            border_style="blue",
        ),
    )

    if eventos:
        grupo_eventos = Group(*eventos[::-1])
    else:
        grupo_eventos = Group("Sem eventos ainda.")

    layout["cenario"].update(
        Panel(
            montar_tabela_mercado(mercados),
            title=f"Mercado Ao Vivo - {algoritmo}",
            border_style="magenta",
        )
    )
    layout["status"].update(grupo_status)
    layout["finalizados"].update(
        Panel(
            montar_tabela_finalizados(resultados),
            title="Traders Finalizados",
            border_style="green",
        )
    )
    layout["eventos"].update(
        Panel(
            grupo_eventos,
            title="Fita de Eventos",
            border_style="white",
        )
    )
    return layout


def desenhar_gantt(gantt: List[Tuple[str, float, float]]) -> str:
    blocos = []

    for nome, inicio, fim in gantt:
        blocos.append(f"| {nome} ({inicio:.2f}s->{fim:.2f}s) ")

    return "".join(blocos) + "|"


def simular_tempo_real_fcfs(
    processos: List[TraderProcesso],
    quantidade_empresas: int,
    exibir_visual: bool = False,
) -> ResultadoEscalonamento:
    return simular_tempo_real(processos, quantidade_empresas, "FCFS", exibir_visual)


def simular_tempo_real_sjf(
    processos: List[TraderProcesso],
    quantidade_empresas: int,
    exibir_visual: bool = False,
) -> ResultadoEscalonamento:
    return simular_tempo_real(processos, quantidade_empresas, "SJF", exibir_visual)


def simular_tempo_real(
    processos: List[TraderProcesso],
    quantidade_empresas: int,
    algoritmo: str,
    exibir_visual: bool = False,
) -> ResultadoEscalonamento:
    pendentes = sorted(
        enumerate(processos),
        key=lambda item: (item[1].tempo_chegada, item[0]),
    )
    prontos: List[Tuple[int, TraderProcesso]] = []
    resultados: List[ResultadoProcesso] = []
    gantt: List[Tuple[str, float, float]] = []
    eventos: List[str] = []
    atual: Optional[ProcessoEmExecucao] = None
    proximo_indice = 0
    inicio_simulacao = time.perf_counter()
    mercados = criar_mercados(quantidade_empresas)
    rng_mercado = random.Random(SEMENTE_PADRAO + quantidade_empresas + (0 if algoritmo == "FCFS" else 1000))
    registrar_evento(eventos, f"Simulacao {algoritmo} iniciada")

    live = None
    if exibir_visual and RICH_DISPONIVEL:
        live = Live(
            montar_dashboard_simulacao(
                algoritmo,
                processos,
                mercados,
                pendentes,
                proximo_indice,
                prontos,
                atual,
                resultados,
                eventos,
                inicio_simulacao,
            ),
            refresh_per_second=20,
            console=CONSOLE,
            transient=False,
        )
        live.__enter__()

    def atualizar_painel():
        if live is not None:
            live.update(
                montar_dashboard_simulacao(
                    algoritmo,
                    processos,
                    mercados,
                    pendentes,
                    proximo_indice,
                    prontos,
                    atual,
                    resultados,
                    eventos,
                    inicio_simulacao,
                )
            )

    try:
        while proximo_indice < len(pendentes) or prontos or atual is not None:
            relogio = time.perf_counter() - inicio_simulacao
            proximo_indice = registrar_chegadas(
                pendentes,
                proximo_indice,
                prontos,
                relogio,
                eventos,
            )
            atualizar_painel()

            if atual is None:
                if not prontos:
                    if proximo_indice >= len(pendentes):
                        break

                    proxima_chegada = pendentes[proximo_indice][1].tempo_chegada
                    tempo_restante = proxima_chegada - (time.perf_counter() - inicio_simulacao)
                    if tempo_restante > 0:
                        time.sleep(min(PASSO_ATUALIZACAO, tempo_restante))
                    continue

                indice_escolhido, processo = selecionar_processo(prontos, algoritmo)
                prontos.remove((indice_escolhido, processo))
                inicio_execucao = time.perf_counter() - inicio_simulacao
                atual = ProcessoEmExecucao(
                    nome=processo.nome,
                    empresa_alvo=processo.empresa_alvo,
                    inicio=inicio_execucao,
                    duracao=processo.tempo_execucao,
                )
                registrar_evento(
                    eventos,
                    f"{processo.nome} assumiu a CPU pelo algoritmo {algoritmo}",
                )
                atualizar_painel()

                fim_previsto = time.perf_counter() + processo.tempo_execucao
                proxima_operacao = time.perf_counter()
                while True:
                    relogio = time.perf_counter() - inicio_simulacao
                    proximo_indice = registrar_chegadas(
                        pendentes,
                        proximo_indice,
                        prontos,
                        relogio,
                        eventos,
                    )
                    agora_absoluto = time.perf_counter()
                    if agora_absoluto >= proxima_operacao:
                        aplicar_operacao_mercado(mercados, processo, rng_mercado, eventos)
                        proxima_operacao = agora_absoluto + 0.12
                    restante = fim_previsto - time.perf_counter()
                    atualizar_painel()
                    if restante <= 0:
                        break
                    time.sleep(min(PASSO_ATUALIZACAO, restante))

                fim_execucao = time.perf_counter() - inicio_simulacao
                espera = max(0.0, inicio_execucao - processo.tempo_chegada)
                resultado = ResultadoProcesso(
                    nome=processo.nome,
                    empresa_alvo=processo.empresa_alvo,
                    tempo_chegada=processo.tempo_chegada,
                    tempo_execucao=processo.tempo_execucao,
                    inicio=inicio_execucao,
                    fim=fim_execucao,
                    espera=espera,
                )
                resultados.append(resultado)
                gantt.append((processo.nome, inicio_execucao, fim_execucao))
                registrar_evento(
                    eventos,
                    f"{processo.nome} concluiu execucao com espera {formatar_tempo(espera)}",
                )
                atual = None
                atualizar_painel()

        return consolidar_resultado(algoritmo, resultados, gantt)
    finally:
        if live is not None:
            live.__exit__(None, None, None)


def imprimir_sem_rich(processos, resultado_fcfs, resultado_sjf):
    print("\nSIMULACAO DE ESCALONAMENTO")
    print("=" * 70)
    print("\nCenario gerado:")
    for processo in processos:
        print(
            f"{processo.nome} | {processo.empresa_alvo} | "
            f"chegada={formatar_tempo(processo.tempo_chegada)} | "
            f"execucao={formatar_tempo(processo.tempo_execucao)}"
        )

    for resultado in [resultado_fcfs, resultado_sjf]:
        print(f"\nAlgoritmo: {resultado.algoritmo}")
        print("-" * 70)
        for item in resultado.resultados:
            print(
                f"{item.nome} | inicio={formatar_tempo(item.inicio)} | "
                f"fim={formatar_tempo(item.fim)} | "
                f"tempo de espera={formatar_tempo(item.espera)}"
            )
        print(f"Soma total dos tempos de espera: {formatar_tempo(resultado.total_espera)}")
        print(f"Tempo medio de espera: {formatar_tempo(resultado.media_espera)}")
        print(f"Gantt: {desenhar_gantt(resultado.gantt)}")


def imprimir_com_rich(processos, resultado_fcfs, resultado_sjf):
    CONSOLE.print("\n[bold cyan]RESULTADO FINAL DA APRESENTACAO[/bold cyan]")

    for resultado in [resultado_fcfs, resultado_sjf]:
        resumo = (
            f"Soma total dos tempos de espera: {formatar_tempo(resultado.total_espera)}\n"
            f"Tempo medio de espera: {formatar_tempo(resultado.media_espera)}\n"
            f"Gantt: {desenhar_gantt(resultado.gantt)}"
        )
        CONSOLE.print(
            Panel(
                montar_tabela_resultados(resultado),
                title=f"Resultado - {resultado.algoritmo}",
                border_style="green" if resultado.algoritmo == "SJF" else "yellow",
            )
        )
        CONSOLE.print(Panel(resumo, title=f"Resumo - {resultado.algoritmo}", border_style="magenta"))


def main():

    quantidade_empresas = int(input("quantidade de empresas->"))
    quantidade_traders = int(input("quantidade de traders->"))
    tempo_maximo_chegada = float(input("tempo maximo de chegada em segundos->"))
    tempo_maximo_execucao = float(input("tempo maximo de execucao em segundos-> "))

    processos = gerar_processos_tempo_real(
        quantidade_empresas,
        quantidade_traders,
        tempo_maximo_chegada,
        tempo_maximo_execucao,
    )

    if RICH_DISPONIVEL:
        CONSOLE.print("\n[bold yellow]Apresentando simulacao ao vivo do FCFS...[/bold yellow]")
    resultado_fcfs = simular_tempo_real_fcfs(
        processos,
        quantidade_empresas,
        exibir_visual=RICH_DISPONIVEL,
    )

    if RICH_DISPONIVEL:
        time.sleep(1)
        CONSOLE.print("\n[bold yellow]Apresentando simulacao ao vivo do SJF...[/bold yellow]")
    resultado_sjf = simular_tempo_real_sjf(
        processos,
        quantidade_empresas,
        exibir_visual=RICH_DISPONIVEL,
    )

    if RICH_DISPONIVEL:
        imprimir_com_rich(processos, resultado_fcfs, resultado_sjf)
    else:
        imprimir_sem_rich(processos, resultado_fcfs, resultado_sjf)


if __name__ == "__main__":
    main()
