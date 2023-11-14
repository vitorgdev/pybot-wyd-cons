import os
import pyautogui
import pydirectinput
import win32gui
import win32con
import win32api
import win32ui
import cv2
import mss
import pygetwindow as gw
import time
import numpy as np
from ctypes import windll
import ctypes
from telegram import Bot
import asyncio
from PIL import ImageGrab


TOKEN = "6728943072:AAE5x9vtjipPfXDUxMSZ_pV3qsvglsTNNgU"
CHAT_ID = "5068582919"


def capturar_screenshot_da_janela(hwnd, nome_arquivo="screenshot.png"):
    try:
        # Usa pygetwindow para obter o objeto da janela
        janela = gw.getWindowsWithTitle("With Your Destiny")[
            0
        ]  # Substitua 'titulo_da_janela' pelo nome real da janela

        # Se a janela foi minimizada, traz ela de volta antes de tirar o screenshot
        if janela.isMinimized:
            janela.restore()

        # Aguarda um momento para a janela ser restaurada antes de tirar o screenshot
        time.sleep(0.2)

        # Captura a tela da região da janela
        x, y, largura, altura = janela.left, janela.top, janela.width, janela.height
        screenshot = ImageGrab.grab(bbox=(x, y, x + largura, y + altura))
        screenshot.save(nome_arquivo)
        return nome_arquivo
    except IndexError:
        print("Janela não encontrada.")
        return None


async def enviar_mensagem_telegram(bot_token, chat_id, mensagem, imagem=None):
    bot = Bot(token=bot_token)

    await bot.send_message(chat_id=chat_id, text=mensagem)
    if imagem:
        with open(imagem, "rb") as photo:
            await bot.send_photo(chat_id=chat_id, photo=photo)


def instalar_pacote(pacote):
    os.system(f"pip install {pacote}")


async def encontrar_janela(nome_janela):
    try:
        return gw.getWindowsWithTitle(nome_janela)[0]
    except IndexError:
        print("Não foi possível encontrar a janela do jogo.")
        await enviar_mensagem_telegram(
            TOKEN, CHAT_ID, "Não foi possível encontrar a janela do jogo."
        )
        exit()


def digitar_texto(hwnd, texto, intervalo=0.05):
    for char in texto:
        if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?':
            win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_SHIFT, 0)
            win32gui.PostMessage(
                hwnd, win32con.WM_CHAR, ord(char.upper()), MAKELPARAM(0, 0x1)
            )
            win32gui.PostMessage(
                hwnd, win32con.WM_KEYUP, win32con.VK_SHIFT, MAKELPARAM(0, 0xC1)
            )
        else:
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(char), MAKELPARAM(0, 0x1))
        time.sleep(intervalo)

    # Simular pressionamento da tecla TAB
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_TAB, 0)
    win32gui.PostMessage(
        hwnd, win32con.WM_KEYUP, win32con.VK_TAB, MAKELPARAM(0, 0xC01F)
    )


def MAKELONG(loWord, hiWord):
    return (hiWord << 16) | loWord


def MAKELPARAM(low, high):
    return (high << 16) | low


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


async def clicar_imagem(hwnd, imagem, confidence=0.9, botao="left", tentativas=10):
    for tentativa in range(tentativas):
        posicao = pyautogui.locateOnScreen(imagem, confidence=confidence)
        if posicao:
            print(f"Imagem encontrada na tentativa {tentativa + 1}!")
            x, y = pyautogui.center(posicao)

            # Traz a janela para o primeiro plano
            await asyncio.sleep(
                0.1
            )  # Pequeno atraso para garantir que a janela esteja ativa

            # Converte coordenadas da tela para coordenadas da janela
            x, y = win32gui.ScreenToClient(hwnd, (x, y))

            lParam = MAKELONG(x, y)
            if botao == "left":
                win32gui.SendMessage(
                    hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam
                )
                win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            elif botao == "right":
                win32gui.SendMessage(
                    hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam
                )
                win32gui.SendMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)
            return True
        else:
            print(f"Imagem não encontrada na tentativa {tentativa + 1}.")
            await asyncio.sleep(1)  # Espera antes de tentar novamente

    if tentativa == tentativas - 1:  # Na última tentativa
        # Captura e salva um screenshot
        screenshot_path = capturar_screenshot_da_janela(hwnd)
        # Envia uma mensagem de erro com o screenshot
        mensagem_bug = f"Bug encontrado, a imagem {imagem} não foi encontrada após {tentativas} tentativas."
        print(mensagem_bug)
        await enviar_mensagem_telegram(
            TOKEN, CHAT_ID, mensagem_bug, imagem=screenshot_path
        )
        return False


def clicar_na_posicao_da_janela(hwnd, posicao_rel_x, posicao_rel_y):
    rect = win32gui.GetWindowRect(hwnd)
    x, y = rect[0] + posicao_rel_x, rect[1] + posicao_rel_y

    ponto = (x, y)
    ponto = win32gui.ScreenToClient(hwnd, ponto)

    lParam = MAKELONG(ponto[0], ponto[1])
    time.sleep(1)  # Pequeno atraso para garantir que a janela esteja ativa
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)


def capturar_janela(hwnd):
    # Restaurar a janela se estiver minimizada
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    # Obter o contexto do dispositivo da janela e criar um contexto de memória
    wdc = win32gui.GetWindowDC(hwnd)
    dcObj = win32ui.CreateDCFromHandle(wdc)
    hdcMemDC = dcObj.CreateCompatibleDC()

    # Obter o tamanho da janela
    left, top, right, bot = win32gui.GetClientRect(hwnd)
    width = right - left
    height = bot - top

    # Criar um bitmap para salvar a imagem
    hBitmap = win32ui.CreateBitmap()
    hBitmap.CreateCompatibleBitmap(dcObj, width, height)

    # Copiar a imagem da janela para o bitmap
    hdcMemDC.SelectObject(hBitmap)
    hdcMemDC.BitBlt((0, 0), (width, height), dcObj, (0, 0), win32con.SRCCOPY)

    # Converter o bitmap em uma imagem do OpenCV
    bmpinfo = hBitmap.GetInfo()
    bmpstr = hBitmap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype="uint8")
    img.shape = (bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4)

    # Exibir a imagem
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # Limpar os objetos do GDI
    win32gui.DeleteObject(hBitmap.GetHandle())
    hdcMemDC.DeleteDC()
    dcObj.DeleteDC()
    win32gui.ReleaseDC(hwnd, wdc)

    # Retornar a imagem
    return img


async def verificar_imagem_periodicamente(hwnd, imagem, intervalo=600):
    template = cv2.imread(imagem, cv2.IMREAD_COLOR)
    if template is None:
        print("Erro: Não foi possível carregar a imagem do template.")
        await enviar_mensagem_telegram(
            TOKEN, CHAT_ID, "Erro: Não foi possível carregar a imagem do template."
        )
        return False

    # Converter o template para escala de cinza, se necessário
    template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    while True:
        screenshot = capturar_janela(hwnd)
        if screenshot is not None:
            # Salvar o screenshot para análise
            cv2.imwrite("screenshot.png", screenshot)

            # Converter o screenshot para escala de cinza, se necessário
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)

            # Certificar-se de que o tipo de dados é o mesmo
            screenshot = screenshot.astype("uint8")
            template = template.astype("uint8")

            # Aplicar o matchTemplate
            res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.6)
            if len(loc[0]) > 0:
                print("Imagem encontrada!")
                await enviar_mensagem_telegram(
                    TOKEN, CHAT_ID, "Jogo foi deslogado, mas já foi logado novamente."
                )
                return True
            else:
                screenshot_path = capturar_screenshot_da_janela(hwnd)
                await enviar_mensagem_telegram(
                    TOKEN, CHAT_ID, "Por enquanto, tudo bem.", screenshot_path
                )
                print("Imagem não encontrada. Aguardando para verificar novamente...")
        else:
            print(
                "Não foi possível tirar o screenshot. Verifique se a janela está minimizada ou oculta."
            )
            await enviar_mensagem_telegram(
                TOKEN,
                CHAT_ID,
                "Não foi possível tirar o screenshot. Verifique se a janela está minimizada ou oculta.",
            )

        time.sleep(intervalo)


def digitar_comando_chat(comando, hwnd):
    press_key(hwnd, "RETURN")
    time.sleep(0.5)

    press_key(hwnd, "/")
    for char in comando.upper():
        press_key(hwnd, char)
    press_key(hwnd, "RETURN")


def press_key(hwnd, key):
    if len(key) == 1:
        win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(key), 0)
    else:
        vk_key = getattr(win32con, "VK_" + key.upper(), None)
        if vk_key is not None:
            win32gui.SetForegroundWindow(hwnd)
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)  # Pressiona a tecla Enter
            win32api.keybd_event(
                win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0
            )  # Solta a tecla Enter


async def tentar_clicar_ate_conseguir(hwnd):
    sucesso_contador = 0  # Inicializa o contador de sucessos
    while (
        sucesso_contador < 2
    ):  # Continua até que o loop tenha sido bem-sucedido duas vezes
        result1 = await clicar_imagem(hwnd, "./imgs/1.png")
        await asyncio.sleep(1)
        if not result1:
            continue  # Tenta novamente se o primeiro clique não for bem-sucedido

        result2 = await clicar_imagem(hwnd, "./imgs/0.png")
        await asyncio.sleep(1)
        if not result2:
            continue  # Tenta novamente se o segundo clique não for bem-sucedido

        sucesso_contador += (
            1  # Incrementa o contador após ambos os cliques serem bem-sucedidos
        )


async def main():
    await enviar_mensagem_telegram(TOKEN, CHAT_ID, "Iniciando o script...")
    # instalar_pacote('opencv-python')
    nome_janela = "With Your Destiny"
    hwnd = win32gui.FindWindow(None, nome_janela)
    time.sleep(4)
    if hwnd:
        print("Janela encontrada!")
        await clicar_imagem(hwnd, "./imgs/global.png")
    else:
        print("Janela não encontrada.")
    time.sleep(2)
    await clicar_imagem(hwnd, "./imgs/global5.png", 0.95)
    time.sleep(2)
    await clicar_imagem(hwnd, "./imgs/conectar.png")

    digitar_texto(hwnd, "vitakusgamer")
    digitar_texto(hwnd, "Titan2011")

    await clicar_imagem(hwnd, "./imgs/login.png")

    time.sleep(1)

    await tentar_clicar_ate_conseguir(hwnd)

    await clicar_imagem(hwnd, "./imgs/confirmar.png")

    time.sleep(1)

    posicao_rel_x = (
        500  # Exemplo: 100 pixels à direita do canto superior esquerdo da janela
    )
    posicao_rel_y = (
        400  # Exemplo: 200 pixels abaixo do canto superior esquerdo da janela
    )

    clicar_na_posicao_da_janela(hwnd, posicao_rel_x, posicao_rel_y)

    time.sleep(0.5)
    await clicar_imagem(hwnd, "./imgs/conectar.png")

    time.sleep(4)
    press_key(hwnd, "i")
    time.sleep(1)
    await clicar_imagem(hwnd, "./imgs/pergaminho.png", confidence=0.6, botao="right")
    time.sleep(8)

    press_key(hwnd, "p")
    time.sleep(1)
    await clicar_imagem(hwnd, "./imgs/checkbox.png", confidence=0.8)
    time.sleep(3)
    digitar_comando_chat("ASSOMBROSA CONS", hwnd)

    imagem_para_verificar = "./imgs/global.png"
    encontrou_imagem = await verificar_imagem_periodicamente(
        hwnd, imagem_para_verificar
    )

    if encontrou_imagem:
        await main()  # Chama a função main novamente


if __name__ == "__main__":
    asyncio.run(main())
