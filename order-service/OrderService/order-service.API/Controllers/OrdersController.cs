using System;
using Microsoft.AspNetCore.Mvc;
using order_service.Application.Services;
using order_service.Application.ViewModels;
using order_service.Application.InputModels;

namespace order_service.API.Controllers;

[ApiController]
[Route("api/[controller]")]
[Produces("application/json")]
public class OrdersController : ControllerBase
{
    private readonly IOrderService _orderService;

    public OrdersController(IOrderService orderService)
    {
        _orderService = orderService;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IEnumerable<OrderViewModel>), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetAll(CancellationToken cancellationToken)
    {
        var orders = await _orderService.GetAllAsync(cancellationToken);
        
        return Ok(orders);
    }

    [HttpGet("{id:guid}")]
    [ProducesResponseType(typeof(OrderViewModel), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> GetById(Guid id, CancellationToken cancellationToken)
    {
        var order = await _orderService.GetByIdAsync(id, cancellationToken);

        return order is null
            ? NotFound( new { message = $"Order with id {id} not found." })
            : Ok(order);
    }

    [HttpPost]
    [ProducesResponseType(typeof(OrderViewModel), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> Create(
        [FromBody] CreateOrderInputModel input, 
        CancellationToken cancellationToken)
    {
        var order = await _orderService.CreateAsync(input, cancellationToken);

        return CreatedAtAction(
            nameof(GetById), 
            new { id = order.Id }, 
            order);
    }

}
