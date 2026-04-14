"""
SALDATERRA — Impressora Bluetooth Android
Imprime comandas automaticamente via Bluetooth (Kapbom KA-1444)
Monitora novos pedidos no Supabase em segundo plano
"""

import threading
import time
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.utils import platform

import supabase_client as db
import bluetooth_printer as bt

# Cor da marca
COR_LARANJA  = (1, 0.48, 0, 1)
COR_FUNDO    = (0.07, 0.07, 0.10, 1)
COR_CARD     = (0.12, 0.12, 0.17, 1)
COR_VERDE    = (0.13, 0.76, 0.37, 1)
COR_VERMELHO = (0.90, 0.25, 0.25, 1)
COR_TEXTO    = (1, 1, 1, 1)
COR_CINZA    = (0.55, 0.55, 0.55, 1)

Window.clearcolor = COR_FUNDO


def salvar_config(mac, intervalo):
    try:
        with open('config.json', 'w') as f:
            json.dump({'mac': mac, 'intervalo': intervalo}, f)
    except Exception:
        pass


def carregar_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {'mac': '', 'intervalo': 10}


class StatusBar(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='horizontal', size_hint_y=None,
                         height=36, padding=(8, 4), spacing=8, **kw)
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*COR_CARD)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        self.dot = Label(text='●', font_size='18sp', size_hint_x=None,
                         width=24, color=COR_CINZA)
        self.txt = Label(text='Parado', font_size='13sp', color=COR_CINZA,
                         halign='left', valign='middle')
        self.txt.bind(size=self.txt.setter('text_size'))
        self.add_widget(self.dot)
        self.add_widget(self.txt)

    def _upd(self, *a):
        self._rect.pos  = self.pos
        self._rect.size = self.size

    def set_status(self, texto, cor):
        self.dot.color = cor
        self.txt.color = cor
        self.txt.text  = texto


class LogBox(ScrollView):
    def __init__(self, **kw):
        super().__init__(size_hint=(1, 1), **kw)
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None,
                                spacing=2, padding=4)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)
        self._linhas = []

    def adicionar(self, texto, cor=None):
        cor = cor or COR_TEXTO
        from datetime import datetime
        hora = datetime.now().strftime('%H:%M:%S')
        lbl = Label(text=f'[{hora}] {texto}', font_size='12sp',
                    color=cor, size_hint_y=None, height=22,
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        self.layout.add_widget(lbl)
        self._linhas.append(lbl)
        # Manter apenas 50 linhas
        if len(self._linhas) > 50:
            old = self._linhas.pop(0)
            self.layout.remove_widget(old)
        Clock.schedule_once(lambda dt: setattr(self, 'scroll_y', 0), 0.1)


class MainLayout(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', spacing=8,
                         padding=(12, 8, 12, 12), **kw)
        cfg = carregar_config()
        self.mac_impressora = cfg.get('mac', '')
        self.intervalo      = cfg.get('intervalo', 10)
        self.rodando        = False
        self._thread        = None
        self._pedidos_impressos = set()

        self._build_ui()
        Clock.schedule_once(lambda dt: self._verificar_coluna(), 1)

    def _build_ui(self):
        # ── Título ──────────────────────────────────────────────
        tit = Label(text='🖨  SALDATERRA', font_size='22sp',
                    bold=True, color=COR_LARANJA,
                    size_hint_y=None, height=44)
        self.add_widget(tit)

        sub = Label(text='Impressora Bluetooth Automática',
                    font_size='13sp', color=COR_CINZA,
                    size_hint_y=None, height=22)
        self.add_widget(sub)

        # ── Status bar ──────────────────────────────────────────
        self.status_bar = StatusBar()
        self.add_widget(self.status_bar)

        # ── Configurações ───────────────────────────────────────
        cfg_box = BoxLayout(orientation='vertical', size_hint_y=None,
                            height=130, spacing=6)
        with cfg_box.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*COR_CARD)
            self._cfg_rect = RoundedRectangle(pos=cfg_box.pos,
                                               size=cfg_box.size, radius=[8])
        cfg_box.bind(
            pos=lambda *a: setattr(self._cfg_rect, 'pos', cfg_box.pos),
            size=lambda *a: setattr(self._cfg_rect, 'size', cfg_box.size)
        )

        # MAC da impressora
        row_mac = BoxLayout(orientation='horizontal', size_hint_y=None,
                            height=40, spacing=6, padding=(8, 4))
        row_mac.add_widget(Label(text='MAC:', font_size='13sp',
                                  color=COR_TEXTO, size_hint_x=None, width=40))
        self.mac_input = TextInput(
            text=self.mac_impressora,
            hint_text='Ex: 00:11:22:33:AA:BB',
            font_size='13sp', multiline=False,
            background_color=(0.18, 0.18, 0.25, 1),
            foreground_color=COR_TEXTO
        )
        self.mac_input.bind(text=self._on_mac_change)

        btn_buscar = Button(text='📡 Buscar', font_size='12sp',
                             size_hint_x=None, width=90,
                             background_color=(0.2, 0.3, 0.6, 1))
        btn_buscar.bind(on_press=self._buscar_dispositivos)

        row_mac.add_widget(self.mac_input)
        row_mac.add_widget(btn_buscar)
        cfg_box.add_widget(row_mac)

        # Intervalo + botao testar
        row2 = BoxLayout(orientation='horizontal', size_hint_y=None,
                         height=40, spacing=6, padding=(8, 4))
        row2.add_widget(Label(text='Intervalo:', font_size='13sp',
                               color=COR_TEXTO, size_hint_x=None, width=70))
        self.spin_intervalo = Spinner(
            text=str(self.intervalo),
            values=['5', '10', '15', '30', '60'],
            font_size='13sp', size_hint_x=None, width=70,
            background_color=(0.18, 0.18, 0.25, 1)
        )
        self.spin_intervalo.bind(text=self._on_intervalo_change)
        row2.add_widget(self.spin_intervalo)
        row2.add_widget(Label(text='segundos', font_size='12sp',
                               color=COR_CINZA))
        btn_testar = Button(text='🧪 Testar conexão', font_size='12sp',
                             background_color=(0.25, 0.25, 0.35, 1))
        btn_testar.bind(on_press=self._testar_conexao)
        row2.add_widget(btn_testar)
        cfg_box.add_widget(row2)

        # Botão imprimir teste
        row3 = BoxLayout(orientation='horizontal', size_hint_y=None,
                         height=36, spacing=6, padding=(8, 2))
        btn_teste_imp = Button(text='🖨  Imprimir teste', font_size='12sp',
                                background_color=(0.3, 0.2, 0.5, 1))
        btn_teste_imp.bind(on_press=self._imprimir_teste)
        row3.add_widget(btn_teste_imp)
        cfg_box.add_widget(row3)

        self.add_widget(cfg_box)

        # ── Botão ligar/desligar ─────────────────────────────────
        self.btn_toggle = Button(
            text='▶  INICIAR MONITORAMENTO',
            font_size='16sp', bold=True,
            size_hint_y=None, height=56,
            background_color=COR_VERDE
        )
        self.btn_toggle.bind(on_press=self._toggle_servico)
        self.add_widget(self.btn_toggle)

        # ── Contador de pedidos ──────────────────────────────────
        self.lbl_contador = Label(
            text='Pedidos impressos hoje: 0',
            font_size='13sp', color=COR_CINZA,
            size_hint_y=None, height=24
        )
        self.add_widget(self.lbl_contador)
        self._contador = 0

        # ── Log ─────────────────────────────────────────────────
        self.add_widget(Label(text='Log de atividades:', font_size='12sp',
                               color=COR_CINZA, size_hint_y=None, height=20,
                               halign='left'))
        self.log = LogBox()
        self.add_widget(self.log)

    # ── Handlers ────────────────────────────────────────────────

    def _on_mac_change(self, inst, val):
        self.mac_impressora = val.strip()
        salvar_config(self.mac_impressora, self.intervalo)

    def _on_intervalo_change(self, inst, val):
        try:
            self.intervalo = int(val)
            salvar_config(self.mac_impressora, self.intervalo)
        except Exception:
            pass

    def _buscar_dispositivos(self, *a):
        self.log_info('Buscando dispositivos pareados...')
        devices = bt.listar_dispositivos_pareados()
        if not devices:
            self.log_erro('Nenhum dispositivo pareado encontrado.')
            self.log_info('Pareie a KA-1444 no Bluetooth do celular primeiro!')
            return

        items = [f"{d['nome']}  ({d['mac']})" for d in devices]
        content = BoxLayout(orientation='vertical', spacing=8, padding=12)
        content.add_widget(Label(text='Selecione a impressora:',
                                  font_size='14sp', size_hint_y=None, height=30))
        popup = Popup(title='Dispositivos Bluetooth',
                      content=content, size_hint=(0.9, 0.7))

        for d in devices:
            btn = Button(text=f"{d['nome']}\n{d['mac']}",
                          font_size='13sp', size_hint_y=None, height=60)
            mac = d['mac']
            def _sel(inst, m=mac):
                self.mac_input.text = m
                self.log_ok(f'Impressora selecionada: {m}')
                popup.dismiss()
            btn.bind(on_press=_sel)
            content.add_widget(btn)

        popup.open()

    def _testar_conexao(self, *a):
        self.log_info('Testando conexão com Supabase...')
        def _run():
            ok = db.testar_conexao()
            if ok:
                self.log_ok('✅ Supabase conectado com sucesso!')
            else:
                self.log_erro('❌ Falha ao conectar no Supabase. Verifique a internet.')
        threading.Thread(target=_run, daemon=True).start()

    def _imprimir_teste(self, *a):
        mac = self.mac_impressora
        if not mac:
            self.log_erro('Configure o MAC da impressora primeiro!')
            return
        pedido_teste = {
            'numero_pedido': 'TESTE',
            'cliente_nome': 'Cliente Teste',
            'cliente_telefone': '(81) 99999-9999',
            'endereco_entrega': 'Rua Teste, 123',
            'bairro': 'Centro',
            'itens': [
                {'nome': 'X-Burguer Especial', 'quantidade': 2, 'preco_unitario': 18.50, 'observacao': 'sem cebola'},
                {'nome': 'Coca-Cola 350ml', 'quantidade': 1, 'preco_unitario': 6.00}
            ],
            'forma_pagamento': 'PIX',
            'valor_total': 43.00,
            'taxa_entrega': 5.00,
        }
        self.log_info(f'Enviando teste para {mac}...')
        def _run():
            ok = bt.imprimir_pedido(mac, pedido_teste)
            if ok:
                self.log_ok('✅ Impressão de teste enviada!')
            else:
                self.log_erro('❌ Falha na impressão. Verifique o Bluetooth e o MAC.')
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_servico(self, *a):
        if self.rodando:
            self._parar()
        else:
            self._iniciar()

    def _iniciar(self):
        if not self.mac_impressora:
            self.log_erro('Configure o MAC da impressora antes de iniciar!')
            return
        self.rodando = True
        self.btn_toggle.text = '⏹  PARAR MONITORAMENTO'
        self.btn_toggle.background_color = COR_VERMELHO
        self.status_bar.set_status(f'Monitorando... (a cada {self.intervalo}s)', COR_VERDE)
        self.log_ok(f'Monitoramento iniciado! Intervalo: {self.intervalo}s')
        self.log_info(f'Impressora: {self.mac_impressora}')
        self._manter_tela_ligada(True)
        self._thread = threading.Thread(target=self._loop_monitoramento, daemon=True)
        self._thread.start()

    def _parar(self):
        self.rodando = False
        self.btn_toggle.text = '▶  INICIAR MONITORAMENTO'
        self.btn_toggle.background_color = COR_VERDE
        self.status_bar.set_status('Parado', COR_CINZA)
        self.log_info('Monitoramento pausado.')
        self._manter_tela_ligada(False)

    def _loop_monitoramento(self):
        """Loop principal rodando em thread separada."""
        while self.rodando:
            try:
                pedidos = db.buscar_pedidos_novos()
                for pedido in pedidos:
                    pid = pedido.get('id')
                    if pid in self._pedidos_impressos:
                        continue

                    num = pedido.get('numero_pedido', '?')
                    self.log_info(f'Novo pedido #{num} recebido!')

                    ok = bt.imprimir_pedido(self.mac_impressora, pedido)
                    if ok:
                        self._pedidos_impressos.add(pid)
                        db.marcar_como_impresso(pid)
                        self._contador += 1
                        self.log_ok(f'✅ Pedido #{num} impresso!')
                        self._atualizar_contador()
                    else:
                        self.log_erro(f'❌ Falha ao imprimir pedido #{num}')

            except Exception as e:
                self.log_erro(f'Erro no monitoramento: {e}')

            # Aguarda intervalo configurado
            for _ in range(self.intervalo * 2):
                if not self.rodando:
                    return
                time.sleep(0.5)

    @mainthread
    def _atualizar_contador(self):
        self.lbl_contador.text = f'Pedidos impressos hoje: {self._contador}'

    @mainthread
    def log_info(self, txt):
        self.log.adicionar(txt, COR_CINZA)

    @mainthread
    def log_ok(self, txt):
        self.log.adicionar(txt, COR_VERDE)

    @mainthread
    def log_erro(self, txt):
        self.log.adicionar(txt, COR_VERMELHO)

    def _manter_tela_ligada(self, ativo):
        """Mantém a tela ligada enquanto monitorando (Android)."""
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            WindowManager = autoclass('android.view.WindowManager$LayoutParams')
            if ativo:
                activity.getWindow().addFlags(WindowManager.FLAG_KEEP_SCREEN_ON)
            else:
                activity.getWindow().clearFlags(WindowManager.FLAG_KEEP_SCREEN_ON)
        except Exception:
            pass

    def _verificar_coluna(self):
        """Verifica se a coluna 'impresso' existe no Supabase."""
        self.log_info('Verificando configuração do banco...')
        def _run():
            resultado = db._request('GET', 'pedidos?select=impresso&limit=1')
            if resultado is None:
                self.log_erro('⚠️  Coluna "impresso" não existe!')
                self.log_info('Execute no Supabase SQL Editor:')
                self.log_info('ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS impresso BOOLEAN DEFAULT FALSE;')
            else:
                self.log_ok('✅ Banco configurado corretamente!')
                self.log_info('Pronto para monitorar pedidos.')
        threading.Thread(target=_run, daemon=True).start()


class SaldaterraApp(App):
    def build(self):
        self.title = 'Saldaterra Impressora'
        return MainLayout()

    def on_pause(self):
        # Permite minimizar sem fechar o app
        return True

    def on_resume(self):
        pass


if __name__ == '__main__':
    SaldaterraApp().run()
