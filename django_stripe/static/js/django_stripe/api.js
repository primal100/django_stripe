const csrfToken =  document.querySelector('input[name="csrfmiddlewaretoken"]').value;
const headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken}
const subscriptionUrl = config.subscription_api_url;
const setupIntentsUrl = config.setup_intents_url;
let selectedPriceId = null;


async function checkResponse(response){
   const data = await response.json();
   if (response.status > 204){
      const errorKey = Object.keys(data)[0];
      const errorValue = data[errorKey];
      const errorMsg = `${errorKey}: ${errorValue}`
      return {error: errorMsg};
   } else {
      return data;
   }
}

async function createSetupIntent() {
  try {
    const response = await fetch(setupIntentsUrl, {
      method: 'POST',
      headers: headers
    });
    return await checkResponse(response);
  } catch (err) {
    return {error: err.message};
  }
}


async function createSubscription(paymentMethodId) {
  try {
    const response = await fetch(subscriptionUrl, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
            default_payment_method: paymentMethodId,
            price_id: selectedPriceId
      })
    });
    return await checkResponse(response);
  } catch (err) {
    return {error: err.message};
  }
}


async function modifySubscription(subscriptionId, paymentMethodId) {
  try {
    const response = await fetch(`${subscriptionUrl}${subscriptionId}/`, {
      method: 'PUT',
      headers: headers,
      body: JSON.stringify({
            default_payment_method: paymentMethodId,
      })
    });
    return await checkResponse(response);
  } catch (err) {
    return {error: err.message};
  }
}


async function cancelSubscription(subscriptionId) {
  try {
    const response = await fetch(`${subscriptionUrl}${subscriptionId}/` , {
      method: 'DELETE',
      headers: headers
    });
    return await checkResponse(response);
  } catch (err) {
    return {error: err.message};
  }
}


