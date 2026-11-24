const todayInJapan = new Date(Date.now() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
const pastUpdates = document.getElementById('past-update-list');

for (const card of document.querySelectorAll('#home-updates [data-update-end], #current-updates [data-update-end]')) {
  if (card.dataset.updateEnd >= todayInJapan) continue;
  if (pastUpdates) {
    pastUpdates.prepend(card);
  } else {
    card.remove();
  }
}
