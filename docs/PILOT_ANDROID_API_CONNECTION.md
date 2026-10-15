# Ligação Android à API

O APK não embute Python/FastAPI. No piloto LAN, o Windows executa o backend e o Android deve usar o endereço LAN completo do computador, nunca `127.0.0.1`.

Configurar no ecrã administrativo do aplicativo: URL `http://IP-LAN:PORTA`, testar ligação, guardar e verificar timestamp/erro. Expor apenas na rede local e preservar autenticação/RBAC. HTTPS e acesso fora da LAN exigem infraestrutura futura.
