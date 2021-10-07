// Format a price (assuming a two-decimal currency like EUR or USD for simplicity).
  function formatPrice(amount, currency) {
    let price = (amount / 100).toFixed(2);
    let numberFormat = new Intl.NumberFormat(['en-US'], {
      style: 'currency',
      currency: currency,
      currencyDisplay: 'symbol',
    });
    return numberFormat.format(price);
  }

  function getPriceText(elem){
    const parentElem = elem.closest(".pricing-option");
    const priceData = parentElem.dataset;
    let currency = priceData.currency;
    let amount = priceData.unit_amount;
    let interval = priceData.interval;
    let value = formatPrice(amount, currency);
    if (interval) value += "/" + interval;
    return value;
  }


(() => {
  'use strict';
  document.querySelectorAll('.price-number').forEach(elem => {
    elem.textContent = getPriceText(elem);
  })
})();