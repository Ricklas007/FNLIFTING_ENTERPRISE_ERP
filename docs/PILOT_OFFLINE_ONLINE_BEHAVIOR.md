# Comportamento offline/online

O frontend pode carregar assets em cache, mas as operações de negócio dependem da API. O piloto não declara offline integral: dados não devem ser apresentados como atuais sem timestamp de sincronização; formulários/fila só são suportados onde implementados pelo módulo.

Sem servidor LAN/HTTPS acessível, login, gravações, anexos, PDFs, GPS físico e sincronização são `BLOCKED_EXTERNAL`.
