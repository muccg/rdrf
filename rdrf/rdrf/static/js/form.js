
function get_fields_per_form(table_id) {
    var num_inputs = 0;
    // find the first input field, record _it's_ sequence number ( 0, 1, 2, ..) , call it N
    // and then count the number of inputs with id containing -N-
    // counting -0- naively ( as originally) , breaks when the removed section is the 0th one itself,
    // hence this strategy.

    var first_input = $("#" + table_id).find("input").first();
    var N = $(first_input).attr("id").match(/-(\d+)-/)[1];
    var pattern = "-" + N + "-";

    $("#" + table_id).find('input').each(function() {
        var input = $(this);
        if (input.attr('id').match(new RegExp(pattern))) {
            num_inputs += 1;
        }
    });
    return num_inputs;
}

function get_number_cdes_in_section(table_id) {
    // the number of unique label texts
    var texts = [];
    var result = $("#" + table_id).find("label").each(function() {
        texts.push($(this).text());
    });
    var unique_texts = jQuery.unique(texts);
    return unique_texts.length;
}

function renumber_section_table(table_id) {
    // we need to ensure sequential order of form ids in case of removal from inside formset ...
    // re-number the ids of the form ...
    var fields_per_form = get_fields_per_form(table_id);

    function form_index_generator(fields_per_form) {
        // e,g if there are three fields per form
        // we return 0,0,0,1,1,1,2,2,2,3,3,3,...  for successive calls
        var i = 0;
        var form_num = 0;
        return function() {
            if (i > (fields_per_form - 1)) {
                i = 0;
                form_num += 1;
            }
            else {
                i = i + 1;
            }

            return form_num.toString();
        }
    }

    var num_cdes_in_section = get_number_cdes_in_section(table_id);
    var label_gen = form_index_generator(num_cdes_in_section);
    var input_id_gen = form_index_generator(fields_per_form);
    var input_name_gen = form_index_generator(fields_per_form);

    $("#" + table_id + " > tbody > tr ").each(function(row_index) {
         $(this)
             // update labels ..  ( there will only be N labels in section where N is the number of CDEs ( not inputs ) in the section
                .find("label")
                .each(function() {
                    $(this).attr({
                        // <label for="id_formset_STest-1-CDEName">
                        'for': function(_, old_for) {
                            var new_index_string = label_gen();
                            var new_for = old_for.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_for;
                           }
            });
        });

        $(this)
                // update ids for inputs
                .find("input").each(function() {
                    $(this).attr({
                        'id': function(_, old_id) {
                            var new_index_string = input_id_gen();
                            var new_id = old_id.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_id;
                        },
                        'name': function(_, old_name) {
                            var new_index_string = input_name_gen();
                            var new_name = old_name.replace(/-\d+-/, "-" + new_index_string + "-");
                            return new_name;
                        }
                    });
                });

    });
}
function do_remove(el, table_id, num_rows, total_forms_id, initial_forms_id) {
    var num_rows_left = $("#" + table_id + " > tbody > tr").length;
    var min_rows_to_keep = 1 + num_rows;
    if (num_rows_left <= min_rows_to_keep) {
        // do nothing

        return;
    }
    var tr = $(el).parent();
    var current_row = tr;
    var rows_to_remove = [];
    for (var i = 0; i <= num_rows; i++) {
        rows_to_remove.push(current_row);
        current_row = current_row.prev();
    }
    _.map(rows_to_remove, function(row) {row.remove();});

    // decrement total forms counter on management form
    var old_value = parseInt($('#' + total_forms_id).val());
    var new_value = old_value - 1;
    $('#' + total_forms_id).val(new_value.toString());

    // decrement initial forms counter on management form
    var old_initial_forms_value = parseInt($('#' + initial_forms_id).val());
    var new_initial_forms_value = old_initial_forms_value - 1;
    $('#' + initial_forms_id).val(new_initial_forms_value.toString());

    // renumber all the fields ( labels + inputs ) in case
    // we have removed a field set from inside the formset and have
    // destroyed the sequential ordering

    renumber_section_table(table_id);
}

function rdrf_click_form_field_history(ev, a) {
  var modal;
  ev.preventDefault();
  $.get($(a).attr("href")).then(function(doc) {
    modal = $("<div></div>").html(doc).find(".modal")
        .appendTo("body")
        .modal()
        .on("hidden.bs.modal", function(e) {
          $(e.target).remove();
        });
    rdrf_form_field_history_init(modal, on_restore);
  });

  var on_restore = function(snapshot) {
    // fixme: restoring a value will depend on the type of cde
    $("#" + $(a).parent().attr("for"))
      .val(snapshot.value)
      .addClass("cde-value-updated")
      .removeClass("cde-value-updated", 5000, "easeOutQuad");
    modal.modal("hide");
  };
}

function rdrf_form_field_history_init(modal, restoreCallback) {
  var info = modal.find(".cde-history-data").remove();
  var label = info.attr("data-label");
  var datatype = info.attr("data-cde-datatype");
  var data = $.parseJSON(info.text());
  var chartCanvas = modal.find(".cde-history-chart");

  var parseIsoDatetime = function(str) {
    var m = moment(str, "YYYY-MM-DDTHH:mm:ssZ");
    return m.isValid() ? m.toDate() : null;
  };
  var snapshotTimestamp = function(snapshot) {
    return parseIsoDatetime(snapshot.timestamp);
  };
  var snapshotValue = function(datatype) {
    if (datatype === "integer" || datatype === "float") {
      return function(snapshot) {
        return _.isNumber(snapshot.value) ? snapshot.value : null;
      };
    } else if (datatype === "boolean") {
      return function(snapshot) {
        return _.isNull(snapshot.value) || _.isUndefined(snapshot.value)
          ? null : snapshot.value ? 1 : 0;
      };
    } else if (datatype === "date") {
      return function(snapshot) {
        return parseIsoDatetime(snapshot.value);
      };
    } else {
      return function(snapshot) {
        return snapshot.value;
      };
    }
  };

  var setupChart = function(ctx) {
    var pairs = _.filter(_.zip(_.map(data, snapshotTimestamp),
                               _.map(data, snapshotValue(datatype))),
                         function(p) { return !_.isNull(p[1]); });
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: _.map(pairs, function(p) { return p[0]; }),
        datasets: [{
          label: label,
          data: _.map(pairs, function(p) { return p[1]; }),
          fill: false,
          lineTension: 0
        }]
      },
      options: {
        legend: {
          display: false
        },
        scales: {
          xAxes: [{
            type: "time",
            position: "bottom",
            time: {
              tooltipFormat: "D-M-Y HH:mm"
            }
          }],
          yAxes: false && datatype === "date" ? [{
            // fixme: chart.js doesn't like time scale on y-axis
            type: "time",
            position: "left"
          }] : undefined
        },
        maintainAspectRatio: false
      }
    });
  };

  var setupRestore = function() {
    // run a callback when one of the restore buttons is clicked
    modal.find("tbody").on("click", ".cde-history-restore", function(ev) {
      ev.stopPropagation();
      var id = $(this).attr("data-id");
      var snapshot = _.find(data, function(s) { return s.id === id });
      if (restoreCallback) {
        restoreCallback(snapshot);
      }
    });
  };

  setupRestore();

  if (_.contains(["integer", "float", "boolean", "date"], datatype)) {
    setupChart(chartCanvas);
  } else {
    chartCanvas.replaceWith("<p>This type of data element can't be plotted.</p>");
    modal.find("a[href='#cde-history-chart']").parent().addClass("disabled");
  }
}
