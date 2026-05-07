using System.Text.Json.Serialization;


namespace order_service.Application.Events;

public sealed record OrderAnalyzedEvent(
    [property: JsonPropertyName("order_id")]
    Guid OrderId,
    
    [property: JsonPropertyName("fraud_status")]
    string FraudStatus,  // "approved" ou "rejected"

    [property: JsonPropertyName("analyze_at")]
    DateTime AnalyzedAt 
);
