# Limitações conhecidas

- Não foi feita instalação interativa Windows nesta execução.
- Não havia dispositivo/emulador Android autorizado.
- APK é debug; AAB/assinatura de produção não foram gerados.
- Docker, PostgreSQL cloud, MinIO, SerpApi live, Traccar/GPS físico e mapa offline licenciado permanecem externos.
- Lint do frontend já tinha sido validado no checkpoint anterior; o processo npm desta execução ficou preso por processos Node legados e não foi usado como PASS novo.
- O frontend build passou durante `android:build`, com aviso de chunk grande do Vite.
