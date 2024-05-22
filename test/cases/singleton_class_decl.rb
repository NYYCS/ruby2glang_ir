class Configuration
    
    class << self
      
      attr_accessor :settings
  
      def initialize_settings
        @settings = {
          app_name: "MyApp",
          version: "1.0.0",
          environment: "development"
        }
      end