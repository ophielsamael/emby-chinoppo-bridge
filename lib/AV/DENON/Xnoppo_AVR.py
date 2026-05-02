# FILE FOR DENON
import logging
import subprocess
import telnetlib

def get_parametro2(texto,valor_actual):
    valor = input(texto+": ")
    if valor=="":
        valor=valor_actual
    return(valor)

def get_parametro_int2(texto,valor_actual):
    valor=''
    while valor=='':
        valor = input(texto+": ")
        if valor=="":
            result=valor_actual
            valor='0'
        else:
            try:
                result=int(valor)
            except:
                print('Introduzca un numero entero')
    return(result)

def get_confirmation2(texto):
    valor=''
    while valor!='s' and valor!='n':
        valor = input(texto+": ")
        if valor=="s":
            return(0)
        elif valor=="n":
            return(1)
        elif valor=="S":
            return(0)
        elif valor=="N":
            return(1)
        else:
            print('Responda s,S,n o N')

def add_hdmi(id, name, param, hdmi_list):
    hdmi_list_tmp=hdmi_list
    hdmi_input={}
    hdmi_input["Id"]=id
    hdmi_input["Name"]=name
    hdmi_input["Param"]=param
    hdmi_list_tmp.append(hdmi_input)
    return(hdmi_list_tmp)

def get_hdmi_list(config):
    hdmi_intput_list=[]
    # Denon/Marantz Standard Inputs
    hdmi_intput_list=add_hdmi(1,"CD",'SICD\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(2,"DVD",'SIDVD\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(3,"Blu-ray (BD)",'SIBD\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(4,"TV AUDIO(TV)",'SITV\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(5,"CBL/SAT",'SISAT/CBL\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(6,"MEDIA PLAYER",'SIMPLAY\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(7,"GAME",'SIGAME\n',hdmi_intput_list)
    hdmi_intput_list=add_hdmi(8,"AUX",'SIAUX\n',hdmi_intput_list)
    
    return(hdmi_intput_list)

def av_check_power(config):
    logging.info('Denon: Comprobando estado de energía...')
    host = config["AV_Ip"]
    port = config.get('AV_Port', 23)

    try:
        with telnetlib.Telnet(host, port, timeout=5) as session:
            session.write(b"PW?\n")
            # Wait for response
            resp = session.read_until(b"\r", timeout=2).decode().strip()
            if "PWON" in resp:
                logging.info("Denon: Ya está ENCENDIDO. No se envía ZMON.")
            else:
                logging.info("Denon: Está en STANDBY. Enviando ZMON...")
                session.write(b"ZMON\n")
    except Exception as e:
        logging.error("Denon: Error comprobando energía: %s", e)
    return("OK")
    
def av_change_hdmi(config):
    logging.info('Llamada a av_change_hdmi')
    host = config["AV_Ip"]
    port = config['AV_Port']
    bsend = config["AV_Input"].encode()
    try:
        with telnetlib.Telnet(host, port, timeout=5) as session:
            session.write(bsend)
            session.write(b"ls\n") # Dummy for some models
            session.write(b"exit\n")
    except Exception as e:
        logging.error("Denon: Error changing HDMI: %s", e)
    return("OK")

def av_get_current_input(config):
    logging.info('Denon: Consultando entrada actual...')
    host = config["AV_Ip"]
    port = config.get('AV_Port', 23)
    try:
        with telnetlib.Telnet(host, port, timeout=3) as session:
            session.write(b"SI?\n")
            resp = session.read_until(b"\r", timeout=2).decode().strip()
            if resp.startswith("SI"):
                # Normalize response to include newline for direct replay if needed
                return resp + "\n"
    except Exception as e:
        logging.error("Denon: Error consultando entrada: %s", e)
    return None

def av_set_input(config, input_str):
    if not input_str:
        return "ERROR"
    logging.info('Denon: Restaurando entrada a %s', input_str.strip())
    host = config["AV_Ip"]
    port = config['AV_Port']
    try:
        with telnetlib.Telnet(host, port, timeout=5) as session:
            session.write(input_str.encode())
            session.write(b"exit\n")
    except Exception as e:
        logging.error("Denon: Error restaurando entrada: %s", e)
    return "OK"

def av_power_off(config):
    logging.info('Llamada a av_power_off')
    host = config["AV_Ip"]
    port = config['AV_Port']
    try:
        with telnetlib.Telnet(host, port, timeout=5) as session:
            session.write(b"ZMOFF\n")
            session.write(b"exit\n")
    except Exception as e:
        logging.error("Denon: Error power off: %s", e)
    return("OK")
