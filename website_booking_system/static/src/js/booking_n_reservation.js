/** @odoo-module **/
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* @License       : https://store.webkul.com/license.html */

import PublicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;

const Days = {
    'sun' : 0,
    'mon' : 1,
    'tue' : 2,
    'wed' : 3,
    'thu' : 4,
    'fri' : 5,
    'sat' : 6,
}
export const BookingWidget = PublicWidget.Widget.extend({
  selector:"#product_detail_main",
  events:{
    'click #booking_and_reservation':'Popup_modal'
  },
  Popup_modal:function(ev){
    var self = this
    var appdiv = $('#booking_modal');
    var bk_loader = $('#bk_n_res_loader');
    var product_id = parseInt(appdiv.data('res_id'),10);
    var redirect = window.location.pathname;
    bk_loader.show();
    jsonrpc("/booking/reservation/modal", {
        'product_id' : product_id,
    })
    .then(function (modal){
      bk_loader.hide();
      var $modal = $(modal);
      $modal.appendTo(appdiv)
          .modal('show')
          .on('hidden.bs.modal', function () {
              $(this).remove();
          });
          // Booking Date Selection Picker
          var dow = { dow: 0 }
          var ws_index = $('#ws_index').text()
          if(ws_index){
            dow = { dow: ws_index }
          }
          var target = document.querySelector('.select_bk_date')
          var default_date = $('#bk_datepicker').data('bk_default_date')
          var bk_select_date = $('#bk_sel_date')
          if (bk_select_date && default_date){
            bk_select_date.val(default_date)
          }
          self.call('datetime_picker',"create",{
            target: target,
            onChange: self._onDateTimePickerChange.bind(self),
            pickerProps: {
                type: "date",
                value: DateTime.fromISO($('#bk_datepicker').data('bk_default_date')),
                minDate : DateTime.fromISO($('#bk_datepicker').data('bk_default_date')),
                maxDate : DateTime.fromISO($('#bk_datepicker').data('bk_end_date')),
            },
          }).enable();
    })

  },
  get_w_closed_days:function(){
    if(w_c_days){
        return w_c_days.map(day => Days[day])
    }
    return []
  },
  reset_total_price:function(){
            var bk_total_price = $('#booking_modal').find('.bk_total_price .oe_currency_value');
            bk_total_price.html('0.00');
        }

,
  _onDateTimePickerChange:function(new_date){
    var date = new_date;
    var self = this;
    var appdiv = $('#booking_modal');
    var bk_loader = $('#bk_n_res_loader');
    var product_id = parseInt(appdiv.data('res_id'),10);
    bk_loader.show();
    jsonrpc("/booking/reservation/modal/update",{
        'product_id' : product_id,
        'new_date' : self.GetFormattedDate(date),
    })
    .then(function (result){
      $('#bk_sel_date').val(date.toISODate(date))
      bk_loader.hide();
      var date_str = [date.monthShort,date.year]
      document.getElementById("dsply_bk_date").innerHTML = date_str.join(", ");
      var bk_slots_main_div = appdiv.find('.bk_slots_main_div');
      self.reset_total_price();
      bk_slots_main_div.html(result);

    })


  },
  GetFormate:function(num){
    if(num<10)
    {
        return '0'+num;
    }
    return num
  },
  GetFormattedDate:function (date) {
    var month = date.month;
    var day = date.day;
    var year = date.year;
    return day + "/" + month + "/" + year;
},
});

PublicWidget.registry.BookingWidget = BookingWidget;

$(document).ready(function() {

        var reset_total_price = function(){
          var bk_total_price = $('#booking_modal').find('.bk_total_price .oe_currency_value');
          bk_total_price.html('0.00');
        }
        // Booking day slot selection
        $('#booking_modal').on('click','.bk_slot_div',
        function(evnt){
            var $this = $(this);
            var booking_modal = $('#booking_modal');
            var bk_modal_slots = booking_modal.find('.bk_modal_slots');
            bk_modal_slots.find('.bk_slot_div').not($this).each(function(){
                var $this = $(this);
                if($this.hasClass('bk_active')){
                    $this.removeClass('bk_active');
                }
            });
            if(!$this.hasClass('bk_active')){
                $this.addClass('bk_active');
            }
            var slot_plans = $this.data('slot_plans');

            var bk_loader = $('#bk_n_res_loader');
            var time_slot_id = parseInt($this.data('time_slot_id'),10);
            var model_plans = booking_modal.find('.bk_model_plans');

            var product_id = parseInt(booking_modal.data('res_id'),10);
            var bk_sel_date = $('#bk_sel_date') || '01-01-93';
            // console.log('bk_sel_date',bk_sel_date.val())
            jsonrpc("/booking/reservation/slot/plans",{
                'time_slot_id' : time_slot_id,
                'slot_plans' : slot_plans,
                'sel_date' : bk_sel_date.val(),
                'product_id' : product_id,
            })
            .then(function (result) {
                bk_loader.hide();
                reset_total_price();
                $('.bk_qty_sel').val('1');
                model_plans.html(result);
            });
          // }
        });

        // Booking Week Day Selection
        $('#booking_modal').on('click','.bk_days',
        function(evnt){
            // debugger;
            var $this = $(this);
            if($this.hasClass('bk_disable')){
                return false;
            };
            var booking_modal = $('#booking_modal');
            var bk_loader = $('#bk_n_res_loader');
            var product_id = parseInt(booking_modal.data('res_id'),10);
            var bk_week_days = booking_modal.find('.bk_week_days');
            var bk_model_cart = booking_modal.find('.bk_model_cart');
            var bk_model_plans = booking_modal.find('.bk_model_plans');
            var bk_slots_n_plans_div = booking_modal.find('.bk_slots_n_plans_div');
            var w_day = $this.data('w_day');
            var w_date = $this.data('w_date');
            var bk_sel_date = $('#bk_sel_date');
            bk_week_days.find('.bk_days').not($this).each(function(){
                var $this = $(this);
                if($this.hasClass('bk_active')){
                    $this.removeClass('bk_active');
                }
            });
            if(!$this.hasClass('bk_active')){
                $this.addClass('bk_active');
            }
            bk_loader.show();
            jsonrpc("/booking/reservation/update/slots",{
                'w_day' : w_day,
                'w_date' : w_date,
                'product_id' : product_id,
            })
            .then(function (result) {
                bk_loader.hide();
                reset_total_price();
                bk_slots_n_plans_div.html(result);
            });
            bk_sel_date.val(w_date);
        });

        // Booking quantity Selection
        $('#booking_modal').on('change','.bk_qty_sel',
        function(evnt){
            var bk_qty = parseInt($(this).val(), 10);
            var booking_modal = $('#booking_modal');
            var bk_base_price = parseFloat(booking_modal.find(".bk_plan_base_price .oe_currency_value").html(), 10);
            var bk_total_price = booking_modal.find('.bk_total_price .oe_currency_value');
            bk_total_price.html((bk_base_price*bk_qty).toFixed(2));
        });
        $('#booking_modal').on('click','.bk-submit',
        function(event){
            var $this = $(this);
            var booking_modal = $('#booking_modal');
            var bk_loader = $('#bk_n_res_loader');
            var product_id = parseInt(booking_modal.data('res_id'),10);
            var bk_model_plans = booking_modal.find('.bk_model_plans').find("input[name='bk_plan']:checked");
            var bk_modal_err = booking_modal.find('.bk_modal_err');
            if(bk_model_plans.length == 0){
                bk_modal_err.html("Please select a plan to proceed further!!!").show();
                setTimeout(function() {
                    bk_modal_err.empty().hide()
                }, 3000);
            }
            else{
                if (!event.isDefaultPrevented() && !$this.is(".disabled")) {
                    bk_loader.show();
                    var wk_date  = $('.bk_days.bk_active').data('w_date')
                    var wk_slot_id = parseInt($('.bk_slot_div.bk_active').data('time_slot_id'))
                    var wk_plan_id = parseInt($('input[name="bk_plan"]:checked').val())
                    jsonrpc("/booking/reservation/cart/validate",{
                        'product_id' : product_id,
                        'wk_date' : wk_date,
                        'wk_slot_id': wk_slot_id,
                        'wk_plan_id' : wk_plan_id,

                    })
                    .then(function (result) {
                        if(result == true){
                            event.preventDefault();
                            $this.closest('form').submit();
                        }
                        else{
                            bk_loader.hide();
                            bk_modal_err.html("This product already in your cart. Please remove it from the cart and try again.").show();
                            setTimeout(function() {
                                bk_modal_err.empty().hide()
                            }, 3000);
                        }
                    });
                }
            }
        });

        // Booking Slot Plan Selection
        $('#booking_modal').on('click', "input[name='bk_plan']",
        function(event){
            var booking_modal = $('#booking_modal');
            var bk_plan_div = $(this).closest('label').find('.bk_plan_div');
            var bk_plan_base_price = $('#booking_modal').find(".bk_plan_base_price .oe_currency_value");
            var base_price = parseFloat(bk_plan_div.data('plan_price'), 10);
            var bk_total_price = booking_modal.find('.bk_total_price .oe_currency_value');
            var bk_qty = parseInt(booking_modal.find('.bk_qty_sel').val(),10);
            var bk_plan_av_qty = parseInt(bk_plan_div.find('.bk_plan_av_qty').text(),10);
            var bk_max_bk_qty = parseInt(booking_modal.find('.bk_max_bk_qty').text(),10);
            $(".bk_plan_av_qty_msg").remove();
            $(".bk_qty_parent_div").removeClass("d-none");
            if(bk_plan_av_qty == 1 || bk_max_bk_qty == 1){
                $(".bk_qty_parent_div").addClass("d-none");
            }
            if(bk_plan_div.hasClass('bk_disable')){
                return false;
            };
            if(isNaN(base_price)){
                base_price = 0.0;
            }
            bk_plan_base_price.html(base_price.toFixed(2));
            bk_total_price.html((base_price).toFixed(2));

            if (bk_plan_av_qty < bk_max_bk_qty){
                var qty = bk_plan_av_qty
                $('.max_capacity_msg').text("(Maximum capacity is "+ bk_plan_av_qty +")")
            }else{
                var qty = bk_max_bk_qty
                $('.max_capacity_msg').text("(Maximum capacity is "+ bk_max_bk_qty +")")
            }
            var i;
            $('.bk_qty_sel').empty()
            for (i = 1; i < qty+1 ; i++)
            {
                $('.bk_qty_sel').append( '<option value="'+i+'">'+i+'</option>' );
            }
        });

        // Click on remove button available on sold out product in cart line
        $('.oe_website_sale').each(function() {
            var oe_website_sale = this;
            $(oe_website_sale).on('click', '.remove-cart-line', function() {
                var $dom = $(this).closest('tr');
                var product = $(this).data('no');
                var line = $(this).data('line')
                // console.log('line',line)
                jsonrpc("/shop/cart/delete", {
                    'line_id': line,
                    'product_id': product,
                })
                .then(function(data) {
                    location.reload();
                });
            });
        });
    });
