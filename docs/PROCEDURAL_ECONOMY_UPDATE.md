# Atualização 0.7 em desenvolvimento

Branch: `feature/procedural-economy-godot-fixes`, baseada na entrega 0.6 e sua investigação de distribuição. Main não recebe commits nem merge automático. Todos os cinco documentos solicitados existem e foram inspecionados, assim como migrações, dependências, API, regras e testes.

Ordem: acesso Android/diagnóstico de conexão e atributos; sequência/geração universal; morte/recuperação e dívida; leilões/eventos; regressões, migração e builds. Dados legados permanecem; novas regras não confiscam nem alteram espólios históricos retroativamente.

Atributos são projeções: base + equipamento + temporários. `power` de arma antiga representa bônus de força; não se altera a base. Status e combate consultam a mesma função. Não há modificadores temporários existentes: parcela explicitamente zero.

Android físico exige URL alcançável terminada em `/api`. `localhost` pertence ao aparelho; `10.0.2.2` serve somente ao emulador. Não existe backend público configurado nesta nuvem. Configurar HTTPS com certificado válido, ou endereço LAN para desenvolvimento, antes de autenticar. O app não contém credenciais administrativas.
