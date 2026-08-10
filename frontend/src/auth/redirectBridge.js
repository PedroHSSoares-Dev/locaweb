import { broadcastResponseToMainFrame } from '@azure/msal-browser/redirect-bridge';

function showFailure() {
  const status = document.getElementById('auth-status');
  if (status) {
    status.textContent = 'Não foi possível concluir o login. Feche esta janela e tente novamente.';
  }
}

broadcastResponseToMainFrame().catch(showFailure);
