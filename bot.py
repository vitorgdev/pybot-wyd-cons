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

def instalar_pacote(pacote):
    os.system(f'pip install {pacote}')

def encontrar_janela(nome_janela):
    try:
        return gw.getWindowsWithTitle(nome_janela)[0]
    except IndexError:
        print("Não foi possível encontrar a janela do jogo.")
        exit()

def digitar_texto(hwnd, texto, intervalo=0.05):
    for char in texto:
        if char.isupper() or char in '!@#$%^&*()_+{}|:"<>?':
            win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_SHIFT, 0)
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(char.upper()), MAKELPARAM(0, 0x1))
            win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_SHIFT, MAKELPARAM(0, 0xC1))
        else:
            win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(char), MAKELPARAM(0, 0x1))
        time.sleep(intervalo)

    # Simular pressionamento da tecla TAB
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_TAB, 0)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_TAB, MAKELPARAM(0, 0xC01F))

def MAKELONG(loWord, hiWord):
    return (hiWord << 16) | loWord

def MAKELPARAM(low, high):
    return (high << 16) | low

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

def clicar_imagem(hwnd, imagem, confidence=0.9, botao="left"):
    posicao = pyautogui.locateOnScreen(imagem, confidence=confidence)
    if posicao:
        print("Imagem encontrada!")
        x, y = pyautogui.center(posicao)
        
        # Traz a janela para o primeiro plano
        time.sleep(0.1)  # Pequeno atraso para garantir que a janela esteja ativa

        # Converte coordenadas da tela para coordenadas da janela
        x, y = win32gui.ScreenToClient(hwnd, (x, y))

        lParam = MAKELONG(x, y)
        if botao == "left":
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
        elif botao == "right":
            win32gui.SendMessage(hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam)
            win32gui.SendMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)
    else:
        print("Imagem não encontrada.")

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
    img = np.frombuffer(bmpstr, dtype='uint8')
    img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)

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

def verificar_imagem_periodicamente(hwnd, imagem, intervalo=2):
    template = cv2.imread(imagem, cv2.IMREAD_COLOR)
    if template is None:
        print("Erro: Não foi possível carregar a imagem do template.")
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
            screenshot = screenshot.astype('uint8')
            template = template.astype('uint8')

            # Aplicar o matchTemplate
            res = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.6)
            if len(loc[0]) > 0:
                print("Imagem encontrada!")
                return True
            else:
                print("Imagem não encontrada. Aguardando para verificar novamente...")
        else:
            print("Não foi possível tirar o screenshot. Verifique se a janela está minimizada ou oculta.")
        
        time.sleep(intervalo)

def pressionar_mouse_na_posicao(janela, posicao_rel_x, posicao_rel_y, duracao):
    x, y, largura, altura = janela.left, janela.top, janela.width, janela.height
    posicao_abs_x = x + posicao_rel_x
    posicao_abs_y = y + posicao_rel_y
    # Mover o cursor para a posição desejada
    pyautogui.moveTo(posicao_abs_x, posicao_abs_y, duration=1)
    
    # Pressionar o botão do mouse
    pyautogui.mouseDown()
    
    # Esperar pelo tempo especificado
    time.sleep(duracao)
    
    # Soltar o botão do mouse
    pyautogui.mouseUp()

def digitar_comando_chat(comando, hwnd):
    press_key(hwnd, 'RETURN')
    time.sleep(0.5)

    press_key(hwnd, '/')
    for char in comando.upper():
        press_key(hwnd, char)
    press_key(hwnd, 'RETURN')

def press_key(hwnd, key):
    if len(key) == 1:
        win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(key), 0)
    else:
        vk_key = getattr(win32con, 'VK_' + key.upper(), None)
        if vk_key is not None:
            win32gui.SetForegroundWindow(hwnd)
            win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)  # Pressiona a tecla Enter
            win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)  # Solta a tecla Enter



def main():
    # instalar_pacote('opencv-python')
    nome_janela = "With Your Destiny"
    hwnd = win32gui.FindWindow(None, nome_janela)
    time.sleep(4)
    if hwnd:
        print("Janela encontrada!")
        clicar_imagem(hwnd, "./imgs/global.png")
    else :
        print("Janela não encontrada.")
    time.sleep(2)
    clicar_imagem(hwnd, "./imgs/global5.png")
    time.sleep(2)
    clicar_imagem(hwnd, "./imgs/conectar.png")

    digitar_texto(hwnd, 'vitakusgamer')
    digitar_texto(hwnd, 'Titan2011')

    clicar_imagem(hwnd,"./imgs/login.png")

    time.sleep(1)

    for _ in range(2):
        clicar_imagem(hwnd, "./imgs/1.png")
        time.sleep(1)
        clicar_imagem(hwnd, "./imgs/0.png")
        time.sleep(1)

    clicar_imagem(hwnd, "./imgs/confirmar.png")

    time.sleep(1)

    posicao_rel_x = 500  # Exemplo: 100 pixels à direita do canto superior esquerdo da janela
    posicao_rel_y = 400  # Exemplo: 200 pixels abaixo do canto superior esquerdo da janela

    clicar_na_posicao_da_janela(hwnd, posicao_rel_x, posicao_rel_y)
    
    time.sleep(0.5)
    clicar_imagem(hwnd, "./imgs/conectar.png")

    time.sleep(4)
    press_key(hwnd, 'i')
    clicar_imagem(hwnd, "./imgs/pergaminho.png", confidence=0.9, botao="right")
    time.sleep(8)

    press_key(hwnd, 'p')
    clicar_imagem(hwnd, "./imgs/checkbox.png")
    time.sleep(3)
    digitar_comando_chat("ASSOMBROSA CONS", hwnd)

    imagem_para_verificar = "./imgs/global.png"
    encontrou_imagem = verificar_imagem_periodicamente(hwnd, imagem_para_verificar)

    if encontrou_imagem:
        main()  # Chama a função main novamente



if __name__ == "__main__":
    main()
