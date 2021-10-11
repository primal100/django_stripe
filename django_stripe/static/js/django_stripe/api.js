/*
Django Rest Framework views require a CSRF Token to be sent with all POST, PUT and DELETE requests
 */

const csrfToken =  document.querySelector('input[name="csrfmiddlewaretoken"]').value;
const headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrfToken}

/*Config set in the django template*/

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
    /*
    Creates a setup intent over the Rest API
     */
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
     /*
    Creates a subscription over the Rest API. The selectedPriceId is set whenever a price object is clicked.
     */
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
    /*
    Change the default payment method for a subscription over the Rest API.
     */
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
     /*
    Cancel a subscription over the Rest API.
     */
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


