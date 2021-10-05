const csrfToken =  document.querySelector('input[name="csrfmiddlewaretoken"]').value;
const headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken}
const subscriptionUrl = config.subscription_api_url;
const setupIntentsUrl = config.setup_intents_url;
let selectedPriceId = null;

async function createSetupIntent() {
  try {
    const response = await fetch(setupIntentsUrl, {
      method: 'POST',
      headers: headers
    });
    const data = await response.json();
    if (data.error) {
      return {error: data.error};
    } else {
      return data;
    }
  } catch (err) {
    return {error: err.message};
  }
}


async function createSubscription(paymentMethodId) {
  try {
    console.log('Creating subscription');
    const response = await fetch(subscriptionUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
            default_payment_method: paymentMethodId,
            price_id: selectedPriceId
      })
    });
    const data = await response.json();
    if (data.error) {
      return {error: data.error};
    } else {
      return data;
    }
  } catch (err) {
    return {error: err.message};
  }
}


async function modifySubscription(subscriptionId, paymentMethodId) {
  try {
    const response = await fetch(`${subscriptionUrl}/${subscriptionId}`, {
      method: 'PUT',
      headers: headers,
      body: JSON.stringify({
            default_payment_method: paymentMethodId,
      })
    });
    const data = await response.json();
    if (data.error) {
      return {error: data.error};
    } else {
      return data;
    }
  } catch (err) {
    return {error: err.message};
  }
}


async function cancelSubscription(subscriptionId) {
  try {
    const response = await fetch(`${subscriptionUrl}/${subscriptionId}` , {
      method: 'DELETE',
      headers: headers
    });
    const data = await response.json();
    if (data.error) {
      return {error: data.error};
    } else {
      return data;
    }
  } catch (err) {
    return {error: err.message};
  }
}


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


function toggleSummary() {
  const summary = document.getElementById('summary');
  summary.classList.toggle(
    'visible',
    selectedPriceId
  );
}

function getPriceText(elem){
  const parentElem = elem.closest(".pricing-option");
  const priceData = parentElem.dataset;
  let currency = priceData.currency;
  let amount = priceData.unit_amount;
  let interval = priceData.interval;
  return formatPrice(amount, currency) + "/" + interval;
}


function onPriceClick(event){
  const priceElem = event.target;
  selectedPriceId = priceElem.id;
  document.querySelector('.total-price').textContent = getPriceText(priceElem);
  toggleSummary();
  const firstFieldElem = document.querySelector('.first-field');
  firstFieldElem.focus();
}

function getSelectedPaymentMethod(){
    let selectedPaymentMethod = null;
    document.querySelectorAll('input[name="payment_method"]').forEach((elem) => {
        console.log([elem.id, elem.checked]);
        if (elem.checked && elem.id !== "select-new-payment-method"){
            selectedPaymentMethod = elem.id;
        }
    })
    console.log(selectedPaymentMethod);
    return selectedPaymentMethod;
}



async function onExistingPaymentMethodClick (){
  //
}


async function onNewPaymentMethodClick(){
  //
}


document.querySelectorAll('.price-number').forEach(elem => {
  elem.textContent = getPriceText(elem);
})

