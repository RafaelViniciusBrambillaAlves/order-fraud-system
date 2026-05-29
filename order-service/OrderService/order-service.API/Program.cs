using Serilog;
using Serilog.Formatting.Json;
using order_service.Application;
using order_service.Infrastructure;
using order_service.Infrastructure.Persistence;
using order_service.Infrastructure.Observability;
using Serilog.Extensions.Hosting;

Log.Logger = new LoggerConfiguration()
    .WriteTo.Console(new JsonFormatter())
    .CreateBootstrapLogger();

try
{    
    var builder = WebApplication.CreateBuilder(args);

    builder.Host.UseSerilog((ctx, services, config) =>
    {
        config 
            .ReadFrom.Configuration(ctx.Configuration)
            .ReadFrom.Services(services)
            .Enrich.WithProperty("service", "order-service")
            .Enrich.FromLogContext();
    }); 

    builder.Services.AddApplication(builder.Configuration);
    builder.Services
        .AddInfrastructure(builder.Configuration)
        .AddObservability(builder.Configuration);


    builder.Services.AddControllers();
    builder.Services.AddEndpointsApiExplorer();
    builder.Services.AddHealthChecks();

    builder.Services.AddSwaggerGen(options =>
    {
        options.SwaggerDoc("v1", new()
        {
            Title = "Order Service API",
            Version = "v1",
            Description = "Manages order creation and lifecycle."
        });

        var xmlFile = $"{System.Reflection.Assembly.GetExecutingAssembly().GetName().Name}.xml";
        var xmlPath = Path.Combine(AppContext.BaseDirectory, xmlFile);
        if (File.Exists(xmlPath))
            options.IncludeXmlComments(xmlPath);
    });

    var app = builder.Build();

    
    app.UseSerilogRequestLogging(options =>
    {
        options.EnrichDiagnosticContext = (diagnosticContext, httpContext) =>
        {
            diagnosticContext.Set("RequestHost", httpContext.Request.Host.Value);
            diagnosticContext.Set("UserAgent", httpContext.Request.Headers["User-Agent"]);
            diagnosticContext.Set("RequestPath", httpContext.Request.Path);
        };
        options.GetLevel = (httpContext, elapsed, ex) => 
            httpContext.Request.Path.StartsWithSegments("/health")
                ? Serilog.Events.LogEventLevel.Verbose
                : Serilog.Events.LogEventLevel.Information;
    });

    await app.Services.ApplyMigrationsAsync();

    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("v1/swagger.json", "Order Service API v1");
        // c.SwaggerEndpoint("/swagger/v1/swagger.json", "Order Service API v1");
        c.RoutePrefix = "swagger";
    });

    // app.UseHttpsRedirection();
    app.UseAuthorization();
    app.MapControllers();
    app.MapHealthChecks("/health");

    app.Run();
}
catch (Exception ex)
{
    Log.Fatal(ex, "order-service terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}