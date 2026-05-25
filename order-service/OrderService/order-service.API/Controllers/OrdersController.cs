using System;
using Microsoft.AspNetCore.Mvc;
using order_service.Application.Services;
using order_service.Application.ViewModels;
using order_service.Application.InputModels;
using System.Diagnostics;

namespace order_service.API.Controllers;

[ApiController]
// [Route("api/[controller]")]
[Route("api/orders")]
[Produces("application/json")]
public class OrdersController : ControllerBase
{
    private readonly IOrderService _orderService;
    private readonly ILogger<OrdersController> _logger;

    public OrdersController(
        IOrderService orderService,
        ILogger<OrdersController> logger)
    {
        _orderService = orderService;
        _logger = logger;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<OrderViewModel>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll(CancellationToken cancellationToken)
    {
        var result = await _orderService.GetAllAsync(cancellationToken);

        var list = result.ToList();
        
        Activity.Current?.SetTag("orders.count", list.Count);

        return Ok(list);
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(OrderViewModel), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(Guid id, CancellationToken cancellationToken)
    {
        var result = await _orderService.GetByIdAsync(id, cancellationToken);

        if (result is null)
            return NotFound();

        Activity.Current?.SetTag("order.id", id.ToString());

        return Ok(result);
    }

    [HttpPost]
    [ProducesResponseType(typeof(OrderViewModel), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateAsync(
        [FromBody] CreateOrderInputModel input, 
        CancellationToken cancellationToken)
    {
        var result = await _orderService.CreateAsync(input, cancellationToken);

        Activity.Current?.SetTag("saga.order_id", result.Id.ToString());

        return CreatedAtAction(
            nameof(GetById), 
            new { id = result.Id }, 
            result);
    }

}
