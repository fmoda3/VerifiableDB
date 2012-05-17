var createUser = function() {
	var getUserFirst = $('<input>');
	getUserFirst.attr('type','text');

	var getUserLast = $('<input>');
	getUserLast.attr('type','text');

	var getUserButton = $('<div>');
	getUserButton.click(function() {
		getUser(getUserFirst.val(), getUserLast.val());	
	});

	var getUser = function (firstname, lastname) {
	
		$.get("localhost/getuser", { 'firstname' : firstname, 'lastname' : lastname }, 
			function(data) {	
		
			}, "json"
		);
	};
};

var createLess = function() {
	var getLess = $('<input>');
	getUserFirst.attr('type','text');
	
	var getLessButton = $('<div>');
	getLessButton.click(function() {
		getLessThan(getLess.val());	
	});	

	var getLessThan = function (balance) {
	
		$.get("localhost/lessthan", { 'balance' : balance }, 
			function(data) {
		
			}, "json"
		);
	}
};

var createrGreater = function() {
	var getGreater = $('<input>');
	getUserFirst.attr('type','text');
	
	var getGreaterButton = $('<div>');
	getGreaterButton.click(function() {
		getGreaterThan(getGreater.val());	
	});

	var getGreaterThan = function (balance) {
	
		$.get("localhost/greaterthan", { 'balance' : balance }, 
			function(data) {
		
			}, "json"
		);
	}
};

var createUpdate = function() {
	var updateUserFirst = $('<input>');
	getUserFirst.attr('type','text');

	var updateUserLast = $('<input>');
	getUserFirst.attr('type','text');

	var updateUserBalance = $('<input>');
	getUserFirst.attr('type','text');

	var updateUserButton = $('<div>');
	updateUserButton.click(function() {
		updateUser(updateUserFirst.val(), updateUserLast.val(), updateUserBalance.val());
	});

	var updateUser = function (firstname, lastname, balance) {
	
		$.post("localhost/updateuser", { 'firstname' : firstname, 'lastname' : lastname, 'balance' : balance  }, 
			function(data) {
			
			}, "json"
		);
	};
};

var createDelete = function() {
	var deleteUserFirst = $('<input>');
	deleteUserFirst.attr('type','text');

	var deleteUserLast = $('<input>');
	deleteUserLast.attr('type','text');

	var deleteUserButton = $('<div>');
	deleteUserButton.click(function() {
		deleteUser(deleteUserFirst.val(), deleteUserLast.val());
	});
	
	var deleteUser = function (firstname, lastname) {
		$.post("localhost/deleteuser", { 'firstname' : firstname, 'lastname' : lastname }, 
			function(data) {
			
			}, "json"
		);
	}
}

	