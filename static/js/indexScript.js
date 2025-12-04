function searchCompany() {
    var input, filter, table, tr, td, i, j, txtValue;
    input = document.getElementById("companySearchText");
    filter = input.value.toUpperCase();
    table = document.getElementById("companyTable");
    tr = table.getElementsByTagName("tr");
    for (i = 1; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td");
        let rowContainsFilter = false;
        for (j = 0; j < td.length; j++) {
            if (td[j]) {
                txtValue = td[j].textContent || td[j].innerText;
                if (txtValue.toUpperCase().indexOf(filter) > -1) {
                    rowContainsFilter = true;
                    break;
                }
            }
        }
        tr[i].style.display = rowContainsFilter ? "" : "none";
    }
}