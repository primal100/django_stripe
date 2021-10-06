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
    const response = await fetch(`${subscriptionUrl}${subscriptionId}/`, {
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
    const response = await fetch(`${subscriptionUrl}${subscriptionId}/` , {
      method: 'DELETE',
      headers: headers
    });
    console.log(response);
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


