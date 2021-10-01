function DjangoStripeClient (stripeInstance, paymentMethodOptions, axiosInstance) {
    this.stripeInstance = stripeInstance;
    this.elements = stripe.elements();
    this.axios = axiosInstance || axios.create();
    this.clientSecret = null;
    this.paymentMethodTypes = null;
    this.successMessage = null;
    this.errorMessage = null;
    this.paymentMethodOptions = paymentMethodOptions || {};
    this.needsNewPaymentMethod = true;
    this.paymentMethodCompleted = null;
    this.priceIdSelector = "#priceId";
    this.start();

    this.start = function() {
        this.setupSubscriptionButton();
        this.refreshPaymentMethods();
    }

    this.getPriceId = function() {
        return document.querySelector(this.priceIdSelector).value;
    }

    this.confirmPaymentMethod = function() {
        return stripe
            .confirmCardSetup(this.client_secret, {
                payment_method: {
                    [this.paymentMethodCompleted]: this.elements.getElement(this.paymentMethodCompleted),
                },
            })
            .then(function (result) {
                if (result.setupIntent) {
                    this.createSubscription(result.setupIntent);
                } else if (result.error) {
                    // Handle result.error
                    this.errorMessage = result.error;
                    console.log(result.error);
                }
            }.bind(this));
    }

    this.onSubmit = function(){
        if (this.paymentMethodCompleted){
            this.confirmPaymentMethod();
        }
    }

    this.getSubscriptionButton = function(){
        return document.getElementById("submit-subscription-form");
    }

    this.setupSubscriptionButton = function(){
        var button = this.getSubscriptionButton();
        button.on("click", this.onSubmit);
        if (this.needsNewPaymentMethod) button.disabled = true;
    }

    this.onAPIRequestError = function(response){
        this.errorMessage = response.data.detail;
    }

    this.onSuccessfulAPIRequest = function(response, onSuccess){
         this.errorMessage = null;
         console.log(response);
         onSuccess(response.data);
    }

    this.runAPIRequest = function(url, method, data, onSuccess){
        data = data || data;
        url = "/api/" + url;
        var axiosObj = {
            url: url,
            method: method,
            data: data,
        }
        console.log(axiosObj);

        return this.axios()
            .then(function (response) {
                this.onSuccessfulAPIRequest(response, onSuccess);
            }.bind(this)
            .error(this.onAPIRequestError));
    }

    this.enablePaymentMethodElement = function(element, paymentMethodType){
        var selector = "#" + paymentMethodType;
        element.mount(selector);
    }

    this.enableExistingPaymentMethodType = function(paymentMethodType){
        var element = this.elements.getElement(paymentMethodType);
        this.enablePaymentMethodElement(element, paymentMethodType);
    }

    this.disablePaymentMethodType = function(paymentMethodType){
        var element = this.elements.getElement(paymentMethodType);
        element.unmount();
    }

    this.getOtherPaymentMethodTypes = function(paymentMethodType){
        return this.paymentMethodTypes.filter(function (v){
            return v !== completedPaymentType;
        })
    }

    this.disableOtherPaymentMethods = function(completedPaymentType){
        var disablePaymentMethods = this.getOtherPaymentMethodTypes(completedPaymentType);
        disablePaymentMethods.forEach(this.disablePaymentMethodType);
    }

    this.enableOtherPaymentMethods = function(paymentMethodType){
        var enablePaymentMethods = this.getOtherPaymentMethodTypes(paymentMethodType);
        enablePaymentMethods.forEach(this.enableExistingPaymentMethodType);
    }

    this.onElementChanged = function(event){
         var submitElement = this.getSubscriptionButton();
         submitElement.disabled = !event.complete;
         if (!this.paymentMethodCompleted === event.elementType && event.complete){
             this.paymentMethodCompleted = event.elementType;
             this.disableOtherPaymentMethods(event.elementType);
         }else if (this.paymentMethodCompleted && !event.complete) {
             this.paymentMethodCompleted = null;
             this.enableOtherPaymentMethods(event.elementType);
         }
        // manage errors
    }

    this.showNewPaymentMethod = function(paymentMethodType) {
        var options = this.paymentMethodOptions[paymentMethodType] || {};
        var element = this.elements.create(paymentMethodType, options);
        this.enablePaymentMethodElement(element, paymentMethodType);
        element.on('change', this.onElementChanged);
    }

    this.onNewSetupIntent = function (data){
        this.clientSecret = data.client_secret;
        this.paymentMethodTypes = data.payment_method_types;
        this.paymentMethodTypes.forEach(this.showNewPaymentMethod);
    }

    this.addPaymentMethods = function(){
        return this.runAPIRequest("setup-intent", "post", {}, this.onNewSetupIntent);
    }

    this.setDefaultPaymentMethod = function(){
        return this.runAPIRequest("default-payment-method", "post", {}, this.refreshPaymentMethods);
    }

    this.onSubscriptionCreate = function(){
        this.successMessage = "You have subscribed successfully."
    }

    this.getSelectedPaymentMethod = function(){

    }

    this.createSubscription = function(setupIntent){
        var paymentMethod;
        if (setupIntent) {
            paymentMethod = setupIntent.payment_method;
        } else{
            paymentMethod = this.getSelectedPaymentMethod();
        }
        var data = {
            price_id: this.getPriceId(),
            default_payment_method: paymentMethod
        }
        return this.runAPIRequest("subscription", "post", {}, this.onSubscriptionCreate)
    }

    this.onConfirmPaymentMethod = function(setupIntent){

    }

    this.confirmPaymentMethod = function(){
    }

    this.onRefreshPaymentMethods = function(data){
        if (data.length > 0){
            this.needsNewPaymentMethod = false;
        } else {
            this.needsNewPaymentMethod = true;
            this.addPaymentMethods();
        }
    }

    this.refreshPaymentMethods = function(){
        return this.runAPIRequest("payment-methods", "get", {}, this.onRefreshPaymentMethods);
    }

    this.onDeletePaymentMethod = function(data){
        this.successMessage = 'Payment method has been deleted';
        this.refreshPaymentMethods();
    }

    this.deletePaymentMethod = function(pmID){
        return this.runAPIRequest("payment-methods", "delete", {}, this.onDeletePaymentMethod);
    }



}