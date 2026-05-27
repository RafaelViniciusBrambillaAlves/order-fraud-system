using order_service.Application;
using order_service.Infrastructure;
using order_service.Infrastructure.Persistence;
using order_service.Infrastructure.Observability;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.Configure(options =>
{
    options.ActivityTrackingOptions =
        ActivityTrackingOptions.TraceId |
        ActivityTrackingOptions.SpanId |
        ActivityTrackingOptions.ParentId;
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

var startupLogger = app.Services.GetRequiredService<ILogger<Program>>();
var connectionString = builder.Configuration.GetConnectionString("default");
startupLogger.LogInformation(
    "Banco de dados configurado | ConnectionString={ConnectionString}",
    connectionString);

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
