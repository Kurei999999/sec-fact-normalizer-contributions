'use strict';
document.getElementById('copy').addEventListener('click', async () => {
  const message = document.getElementById('copy-status');
  try {
    await navigator.clipboard.writeText(document.getElementById('sql').textContent);
    message.textContent = 'SQL copied.';
  } catch {
    message.textContent = 'Select the SQL above and copy it manually.';
  }
});

async function setupTrees() {
  const profileSelect = document.getElementById('tree-profile');
  const statementSelect = document.getElementById('tree-statement');
  const message = document.getElementById('tree-status');
  const content = document.getElementById('tree-content');
  const download = document.getElementById('tree-download');
  let requestNumber = 0;
  let downloadUrl;
  window.addEventListener('pagehide', () => {
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  });
  try {
    const bundle = window.mappingTrees;
    if (!bundle) throw new Error('Tree data unavailable');
    const profiles = bundle.profiles;
    if (!profiles.length) throw new Error('No profiles');
    profileSelect.replaceChildren();
    for (const profile of profiles) {
      profileSelect.add(new Option(profile.label, profile.id));
    }
    profileSelect.disabled = false;
    async function loadTree() {
      const currentRequest = ++requestNumber;
      const profile = profiles.find(item => item.id === profileSelect.value);
      const path = profile.statements[statementSelect.value];
      download.hidden = true;
      content.textContent = '';
      message.textContent = 'Loading selected tree…';
      try {
        const text = bundle.texts[path];
        if (typeof text !== 'string') throw new Error('Tree unavailable');
        if (currentRequest !== requestNumber) return;
        content.textContent = text;
        if (downloadUrl) URL.revokeObjectURL(downloadUrl);
        downloadUrl = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
        download.href = downloadUrl;
        download.download = path.split('/').pop();
        download.hidden = false;
        message.textContent = `${profile.label} / ${statementSelect.value}`;
      } catch {
        if (currentRequest === requestNumber) message.textContent = 'Could not load this tree. Try selecting it again, or browse the mappings on GitHub.';
      }
    }
    function selectProfile() {
      const previous = statementSelect.value;
      const profile = profiles.find(item => item.id === profileSelect.value);
      statementSelect.replaceChildren();
      for (const statement of Object.keys(profile.statements)) {
        statementSelect.add(new Option(statement, statement));
      }
      if (profile.statements[previous]) statementSelect.value = previous;
      statementSelect.disabled = false;
      loadTree();
    }
    profileSelect.addEventListener('change', selectProfile);
    statementSelect.addEventListener('change', loadTree);
    selectProfile();
  } catch {
    message.textContent = 'Mapping trees are unavailable. Browse the mappings on GitHub, or build the website with tools/build_website.py for local preview.';
  }
}
setupTrees();
