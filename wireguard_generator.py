import asyncio
import httpx
import datetime
import json
import base64
import subprocess
import ipaddress
import random
import os
import re

class WireGuardGeneratorError(Exception):
    pass

def generate_keypair():
    try:
        priv_key_proc = subprocess.run(['wg', 'genkey'], capture_output=True, text=True, check=True)
        private_key = priv_key_proc.stdout.strip()
        pub_key_proc = subprocess.run(['wg', 'pubkey'], capture_output=True, text=True, input=private_key, check=True)
        public_key = pub_key_proc.stdout.strip()
        return private_key, public_key
    except FileNotFoundError:
        raise WireGuardGeneratorError("Команда 'wg' не найдена. Убедитесь, что wireguard-tools установлен.")
    except subprocess.CalledProcessError as e:
        raise WireGuardGeneratorError(f"Ошибка при выполнении команды 'wg': {e.stderr}")
    except Exception as e:
        raise WireGuardGeneratorError(f"Непредвиденная ошибка при генерации ключей WireGuard: {e}")

async def register_warp_client(public_key: str) -> dict:
    api_url = "https://api.cloudflareclient.com/v0i1909051800"
    headers = {
        'user-agent': '',
        'content-type': 'application/json'
    }

    try:
        reg_payload = {
            "install_id": "",
            "tos": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            "key": public_key,
            "fcm_token": "",
            "type": "ios",
            "locale": "en_US"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{api_url}/reg", headers=headers, json=reg_payload)
            response.raise_for_status()
            reg_data = response.json()

        client_id = reg_data['result']['id']
        token = reg_data['result']['token']

        patch_headers = {
            'authorization': f'Bearer {token}',
            'content-type': 'application/json'
        }
        patch_payload = {"warp_enabled": True}
        async with httpx.AsyncClient() as client:
            response = await client.patch(f"{api_url}/reg/{client_id}", headers=patch_headers, json=patch_payload)
            response.raise_for_status()
            warp_config = response.json()

        return warp_config['result']['config']

    except httpx.HTTPStatusError as e:
        raise WireGuardGeneratorError(f"Ошибка API Cloudflare: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise WireGuardGeneratorError(f"Ошибка сети при связи с Cloudflare API: {e}")
    except KeyError as e:
        raise WireGuardGeneratorError(f"Неожиданный формат ответа Cloudflare API: Отсутствует ключ {e}")
    except Exception as e:
        raise WireGuardGeneratorError(f"Непредвиденная ошибка при регистрации WARP: {e}")

async def get_endpoint_from_script(script_path="./generate_ip.sh") -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            'bash', script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise WireGuardGeneratorError(f"generate_ip.sh failed: {stderr.decode().strip()}")

        output = stdout.decode().strip()
        if not re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', output):
            raise WireGuardGeneratorError(f"Некорректный формат IP:PORT из скрипта: '{output}'")

        return output
    except Exception as e:
        raise WireGuardGeneratorError(f"Ошибка при вызове скрипта generate_ip.sh: {e}")

def construct_wireguard_config(
    private_key: str,
    client_ipv4: str,
    client_ipv6: str,
    peer_public_key: str,
    endpoint: str
) -> str:
    return f"""[Interface]
PrivateKey = {private_key}
S1 = 0
S2 = 0
Jc = 120
Jmin = 23
Jmax = 911
H1 = 1
H2 = 2
H3 = 3
H4 = 4
MTU = 1280
Address = {client_ipv4}, {client_ipv6}
DNS = 1.1.1.1, 2606:4700:4700::1111, 1.0.0.1, 2606:4700:4700::1001

[Peer]
PublicKey = {peer_public_key}
AllowedIPs = 0.0.0.0/0, ::/0
Endpoint = {endpoint}
"""

async def generate_wireguard_config_full() -> str:
    private_key, public_key = generate_keypair()
    warp_config = await register_warp_client(public_key)

    peer_public_key = warp_config['peers'][0]['public_key']
    client_ipv4 = warp_config['interface']['addresses']['v4']
    client_ipv6 = warp_config['interface']['addresses']['v6']

    endpoint = await get_endpoint_from_script()

    return construct_wireguard_config(
        private_key=private_key,
        client_ipv4=client_ipv4,
        client_ipv6=client_ipv6,
        peer_public_key=peer_public_key,
        endpoint=endpoint
    )

if __name__ == '__main__':
    async def test_generation():
        try:
            print("Генерирую конфиг WireGuard...")
            config = await generate_wireguard_config_full()
            print("\n--- Сгенерированный конфиг ---")
            print(config)
            print("------------------------")
        except WireGuardGeneratorError as e:
            print(f"Ошибка: {e}")

    asyncio.run(test_generation())
